"""Pose detection + scoring module for Raspberry Pi using MediaPipe."""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_pose_detector: MediaPipePoseDetector | None = None
_detector_model_path: Path | None = None
_last_analysis_at = 0.0
_pose_visible = False
# Prefer a responsive overlay on a 10 FPS Pi inference stream.  The previous
# values looked smooth when still, but visibly trailed a person who bent or
# turned quickly.
DEFAULT_OVERLAY_SMOOTHING_ALPHA = 0.65
DEFAULT_OVERLAY_HOLD_SECONDS = 0.2
DEFAULT_OVERLAY_MIN_VISIBILITY = 0.35
# Score values are more sensitive than the visible skeleton to small landmark
# jitter.  A median-of-three rejects a one-frame spike; EMA then makes the
# numbers readable without making the posture state feel delayed.
DEFAULT_METRIC_SMOOTHING_ALPHA = 0.35
METRIC_KEYS = ("score", "neck", "shoulders", "upper_body")

# Keep the live overlay small: these are the points rendered by the dashboard
# skeleton, rather than all 33 MediaPipe landmarks.
OVERLAY_LANDMARK_INDICES = (0, 7, 8, 11, 12, 13, 14, 15, 16)
OVERLAY_CONNECTIONS = (
    # Head/neck should join ears to their own shoulders.  Joining the nose
    # directly to both shoulders made a misleading large triangle on the
    # dashboard even when MediaPipe had found the correct landmarks.
    (0, 7), (0, 8), (7, 11), (8, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
)


class PoseOverlaySmoother:
    """Smooth only the landmarks rendered on the video preview.

    Posture scoring intentionally continues to use the raw MediaPipe output so
    alert timing is not delayed by the visual interpolation.
    """

    def __init__(self) -> None:
        self._points: dict[int, dict[str, float]] = {}

    def reset(self) -> None:
        self._points.clear()

    def update(
        self,
        landmarks: list[dict[str, Any]],
        now: float,
        *,
        alpha: float,
        hold_seconds: float,
        min_visibility: float,
    ) -> list[dict[str, Any]]:
        """Return filtered landmarks and briefly retain reliable lost points."""
        fresh: dict[int, tuple[float, float, float]] = {}
        for landmark in landmarks:
            index = landmark.get("index")
            if not isinstance(index, int):
                continue
            try:
                x = float(landmark.get("x", -1))
                y = float(landmark.get("y", -1))
                visibility = float(landmark.get("visibility", 0))
            except (TypeError, ValueError):
                continue
            if not 0 <= x <= 1 or not 0 <= y <= 1 or visibility < min_visibility:
                continue
            fresh[index] = (x, y, visibility)

        for index, (x, y, visibility) in fresh.items():
            previous = self._points.get(index)
            if previous is None:
                filtered_x, filtered_y = x, y
            else:
                filtered_x = previous["x"] + alpha * (x - previous["x"])
                filtered_y = previous["y"] + alpha * (y - previous["y"])
            self._points[index] = {
                "x": filtered_x,
                "y": filtered_y,
                "visibility": visibility,
                "seen_at": now,
            }

        for index, point in tuple(self._points.items()):
            if now - point["seen_at"] > hold_seconds:
                del self._points[index]

        order = {index: position for position, index in enumerate(OVERLAY_LANDMARK_INDICES)}
        return [
            {
                "index": index,
                "x": round(point["x"], 4),
                "y": round(point["y"], 4),
                "visibility": round(point["visibility"], 4),
            }
            for index, point in sorted(self._points.items(), key=lambda item: order.get(item[0], item[0]))
        ]


class PoseMetricSmoother:
    """Reject transient pose spikes before publishing posture measurements.

    MediaPipe landmarks are deliberately kept raw for drawing.  The dashboard,
    history and LED instead receive a short median + exponential moving
    average, so one uncertain frame cannot turn a stable sitting score into a
    false alert.
    """

    def __init__(self) -> None:
        self._samples: deque[dict[str, float]] = deque(maxlen=3)
        self._metrics: dict[str, float] | None = None

    def reset(self) -> None:
        self._samples.clear()
        self._metrics = None

    def update(self, metrics: dict[str, Any], alpha: float) -> dict[str, Any]:
        sample = {key: float(metrics[key]) for key in METRIC_KEYS}
        self._samples.append(sample)
        medians = {
            key: sorted(item[key] for item in self._samples)[len(self._samples) // 2]
            for key in METRIC_KEYS
        }
        if self._metrics is None:
            self._metrics = medians
        else:
            self._metrics = {
                key: self._metrics[key] + alpha * (medians[key] - self._metrics[key])
                for key in METRIC_KEYS
            }
        return {key: round(self._metrics[key], 1) for key in METRIC_KEYS}


_overlay_smoother = PoseOverlaySmoother()
_metric_smoother = PoseMetricSmoother()


def _overlay_settings(detection: dict[str, Any]) -> tuple[float, float, float, float]:
    """Read validated visual-only smoothing settings with safe defaults."""
    alpha = min(0.95, max(0.05, float(detection.get("overlay_smoothing_alpha", DEFAULT_OVERLAY_SMOOTHING_ALPHA))))
    hold_seconds = min(5.0, max(0.0, float(detection.get("overlay_hold_seconds", DEFAULT_OVERLAY_HOLD_SECONDS))))
    min_visibility = min(1.0, max(0.0, float(detection.get("overlay_min_visibility", DEFAULT_OVERLAY_MIN_VISIBILITY))))
    metric_alpha = min(0.95, max(0.05, float(detection.get("metric_smoothing_alpha", DEFAULT_METRIC_SMOOTHING_ALPHA))))
    return alpha, hold_seconds, min_visibility, metric_alpha


def draw_pose_overlay(
    frame: Any,
    landmarks: list[dict[str, Any]],
    metrics: dict[str, Any] | None = None,
    min_visibility: float = DEFAULT_OVERLAY_MIN_VISIBILITY,
) -> None:
    """Draw the compact Pi-detected skeleton onto the outgoing RGB frame.

    This makes the verification overlay visible even when a dashboard is
    serving an older frontend bundle or the signaling channel is reconnecting.
    """
    if not hasattr(frame, "shape") or len(getattr(frame, "shape", ())) < 2:
        return

    import cv2  # type: ignore

    height, width = frame.shape[:2]
    points: dict[int, tuple[int, int]] = {}
    for landmark in landmarks:
        index = landmark.get("index")
        visibility = float(landmark.get("visibility", 0))
        x = float(landmark.get("x", -1))
        y = float(landmark.get("y", -1))
        if not isinstance(index, int) or visibility < min_visibility or not 0 <= x <= 1 or not 0 <= y <= 1:
            continue
        points[index] = (round(x * (width - 1)), round(y * (height - 1)))

    for start, end in OVERLAY_CONNECTIONS:
        if start in points and end in points:
            cv2.line(frame, points[start], points[end], (0, 255, 0), 2, cv2.LINE_AA)
    for point in points.values():
        cv2.circle(frame, point, 4, (0, 255, 0), -1, cv2.LINE_AA)

    label = "POSE: detecting" if metrics is None else f"POSTURE: {metrics['score']:.0f}/100"
    cv2.putText(frame, label, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)


class MediaPipePoseDetector:
    """Wrapper for MediaPipe Pose landmarker matching frontend posture scoring."""

    def __init__(self, model_path: Path) -> None:
        import mediapipe as mp  # type: ignore

        if not model_path.is_file():
            raise FileNotFoundError(f"Pose Landmarker Full model not found: {model_path}")
        self.mp = mp
        self._last_timestamp_ms = -1
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def calculate_metrics(self, frame: Any, color_space: str = "bgr") -> dict[str, Any] | None:
        import cv2  # type: ignore

        if color_space not in {"bgr", "rgb"}:
            raise ValueError(f"unsupported camera color space: {color_space}")
        rgb = frame if color_space == "rgb" else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = max(int(time.monotonic() * 1000), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        results = self.pose.detect_for_video(image, timestamp_ms)

        if not results.pose_landmarks:
            return None

        landmarks = results.pose_landmarks[0]
        if len(landmarks) < 13:
            return None

        overlay_landmarks = [
            {
                "index": index,
                "x": round(float(landmarks[index].x), 4),
                "y": round(float(landmarks[index].y), 4),
                "visibility": round(float(getattr(landmarks[index], "visibility", 1.0)), 4),
            }
            for index in OVERLAY_LANDMARK_INDICES
        ]

        nose = landmarks[0]
        ls = landmarks[11]
        rs = landmarks[12]

        # A seated person can be evaluated even when the lower body is outside
        # the camera frame.  Ears are helpful but optional; the nose is a
        # reliable fallback for narrow front-facing camera views.
        for pt in [nose, ls, rs]:
            if getattr(pt, "visibility", 1.0) < 0.45:
                return {"landmarks": overlay_landmarks}

        visible_ears = [
            landmarks[index]
            for index in (7, 8)
            if getattr(landmarks[index], "visibility", 1.0) >= 0.45
        ]
        head_points = visible_ears or [nose]

        head_x = sum(point.x for point in head_points) / len(head_points)
        head_y = sum(point.y for point in head_points) / len(head_points)
        head_z = sum(getattr(point, "z", 0.0) for point in head_points) / len(head_points)

        mid_sh_x = (ls.x + rs.x) / 2.0
        mid_sh_y = (ls.y + rs.y) / 2.0
        mid_sh_z = (getattr(ls, "z", 0.0) + getattr(rs, "z", 0.0)) / 2.0

        # 1. Neck metric: side displacement from the shoulder midpoint.
        # MediaPipe's monocular Z includes a person's natural head-to-shoulder
        # depth, so treating its absolute value as a bad-posture angle made a
        # normally seated person score zero.  The stable camera-independent
        # signal here is the visible 2D head/shoulder alignment.
        dx_neck = head_x - mid_sh_x
        dy_neck = mid_sh_y - head_y
        neck_roll = math.atan2(abs(dx_neck), max(0.001, dy_neck)) * 180.0 / math.pi
        neck = neck_roll

        # 2. Shoulder alignment.  An angle (rather than raw pixel distance)
        # remains comparable when the person sits nearer or farther away.
        dx_shoulder = rs.x - ls.x
        dy_shoulder = rs.y - ls.y
        shoulder_roll = math.atan2(abs(dy_shoulder), max(0.001, abs(dx_shoulder))) * 180.0 / math.pi
        shoulders = shoulder_roll
        shoulder_span = max(0.001, math.hypot(dx_shoulder, dy_shoulder))

        # 3. Slouching: a head moving forward becomes deeper than the
        # shoulders.  MediaPipe always includes a small natural depth offset
        # between ears and shoulders, so allow 35% of shoulder width before
        # assigning a slouch angle.  Scaling by shoulder width makes this
        # robust to the camera being closer or farther away.
        # MediaPipe Z decreases toward the camera, so only a head closer than
        # the shoulders counts as a forward slouch.
        head_depth = max(0.0, mid_sh_z - head_z)
        excess_head_depth = max(0.0, head_depth - shoulder_span * 0.35)
        upper_body = math.atan2(excess_head_depth, shoulder_span) * 180.0 / math.pi

        # Angles inside a small neutral range are normal landmark noise.  The
        # calibrated penalties make sustained forward-head posture meaningful
        # without penalising a natural small shift in a seated position.
        neck_penalty = max(0.0, neck - 12.0) * 1.2
        shoulder_penalty = max(0.0, shoulders - 6.0) * 1.0
        slouch_penalty = max(0.0, upper_body - 7.0) * 1.6

        score = max(0.0, min(100.0, 100.0 - neck_penalty - shoulder_penalty - slouch_penalty))

        return {
            "score": round(score, 1),
            "neck": round(neck, 1),
            "shoulders": round(shoulders, 1),
            "upper_body": round(upper_body, 1),
            "landmarks": overlay_landmarks,
        }

    def close(self) -> None:
        self.pose.close()


def get_detector(model_path: str | Path) -> MediaPipePoseDetector:
    global _pose_detector, _detector_model_path
    resolved_model_path = Path(model_path).resolve()
    if _pose_detector is None or _detector_model_path != resolved_model_path:
        if _pose_detector is not None:
            _pose_detector.close()
        try:
            _pose_detector = MediaPipePoseDetector(resolved_model_path)
            _detector_model_path = resolved_model_path
            logger.info("initialized MediaPipe Pose Landmarker Full: %s", resolved_model_path)
        except Exception as exc:
            # Sending fabricated values is worse than temporarily sending no
            # values: it can create false posture alerts and corrupt history.
            raise RuntimeError(f"could not initialize MediaPipe Pose: {exc}") from exc
    return _pose_detector


def close_detector() -> None:
    global _pose_detector, _detector_model_path, _last_analysis_at, _pose_visible
    if _pose_detector is not None:
        _pose_detector.close()
    _pose_detector = None
    _detector_model_path = None
    _last_analysis_at = 0.0
    _pose_visible = False
    _overlay_smoother.reset()
    _metric_smoother.reset()


def process_live_frame(
    frame: Any,
    config: dict,
    uploader: Any,
    alert_controller: Any | None = None,
    color_space: str = "rgb",
    pose_callback: Any | None = None,
    frame_overlay_callback: Any | None = None,
    lcd_display: Any | None = None,
) -> None:
    """Run throttled posture inference on one in-memory live camera frame."""
    global _last_analysis_at, _pose_visible
    detection = config.get("detection", {})
    analysis_interval = max(0.0, float(detection.get("interval", 0)))
    now = time.monotonic()
    if now - _last_analysis_at < analysis_interval:
        return
    _last_analysis_at = now

    model_path = detection.get("model")
    detector = get_detector(model_path) if model_path else get_detector()
    result = detector.calculate_metrics(frame, color_space)
    alpha, hold_seconds, min_visibility, metric_alpha = _overlay_settings(detection)

    if result:
        if not _pose_visible:
            logger.info("pose detected on Pi; publishing skeleton overlay landmarks")
            _pose_visible = True
        raw_landmarks = result.pop("landmarks", [])
        landmarks = _overlay_smoother.update(
            raw_landmarks,
            now,
            alpha=alpha,
            hold_seconds=hold_seconds,
            min_visibility=min_visibility,
        )
        if "score" not in result:
            _metric_smoother.reset()
            if alert_controller is not None:
                alert_controller.clear_posture()
            if lcd_display is not None:
                lcd_display.show_incomplete_pose()
            logger.debug("pose detected but required head/shoulder landmarks are not visible yet; sending overlay without a score")
            if frame_overlay_callback is not None:
                frame_overlay_callback(landmarks, None)
            else:
                draw_pose_overlay(frame, landmarks, min_visibility=min_visibility)
            if pose_callback is not None:
                pose_callback({}, landmarks)
            return
        metrics = _metric_smoother.update(result, metric_alpha)
        if frame_overlay_callback is not None:
            frame_overlay_callback(landmarks, metrics)
        else:
            draw_pose_overlay(frame, landmarks, metrics, min_visibility=min_visibility)
        logger.debug("detected metrics: score=%s, neck=%s°, shoulders=%s°, slouch=%s°",
                     metrics["score"], metrics["neck"], metrics["shoulders"], metrics["upper_body"])
        uploader.send_sample(metrics)

        if lcd_display is not None:
            lcd_display.show_metrics(metrics)

        if alert_controller is not None:
            alert_controller.update(metrics)
        if pose_callback is not None:
            pose_callback(metrics, landmarks)
    else:
        _metric_smoother.reset()
        if alert_controller is not None:
            alert_controller.clear_posture()
        if lcd_display is not None:
            lcd_display.show_waiting_for_pose()
        if _pose_visible:
            logger.info("pose is no longer visible to the Pi camera")
            _pose_visible = False
        logger.debug("no pose landmarks detected in frame")
        landmarks = _overlay_smoother.update(
            [],
            now,
            alpha=alpha,
            hold_seconds=hold_seconds,
            min_visibility=min_visibility,
        )
        if landmarks:
            if frame_overlay_callback is not None:
                frame_overlay_callback(landmarks, None)
            else:
                draw_pose_overlay(frame, landmarks, min_visibility=min_visibility)
            if pose_callback is not None:
                pose_callback({}, landmarks)
            return
        if frame_overlay_callback is not None:
            frame_overlay_callback([], None)
        if pose_callback is not None:
            pose_callback({}, [])


def run_detection_cycle(camera: Any, config: dict, uploader: Any, alert_controller: Any | None = None) -> None:
    """Backward-compatible single-frame path used by focused tests and --once."""
    import cv2  # type: ignore

    ok, frame = camera.read()
    if not ok or frame is None:
        logger.warning("failed to read frame from camera")
        return
    if getattr(camera, "flip", 0):
        frame = cv2.flip(frame, camera.flip)
    if getattr(camera, "color_space", "bgr") == "bgr":
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    process_live_frame(frame, config, uploader, alert_controller)
