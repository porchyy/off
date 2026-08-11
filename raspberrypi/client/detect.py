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
_posture_classifier: Any | None = None
_classifier_model_path: Path | None = None
_failed_classifier_model_path: Path | None = None
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
METRIC_KEYS = ("score", "neck", "shoulders", "torso")

# Keep the live overlay small: these are the points rendered by the dashboard
# skeleton, rather than all 33 MediaPipe landmarks.
OVERLAY_LANDMARK_INDICES = (0, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24)
OVERLAY_CONNECTIONS = (
    # Head/neck should join ears to their own shoulders.  Joining the nose
    # directly to both shoulders made a misleading large triangle on the
    # dashboard even when MediaPipe had found the correct landmarks.
    (0, 7), (0, 8), (7, 11), (8, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
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

    # The browser mirrors its live camera preview like a selfie view. Keep
    # text out of this Pi-burned overlay so labels never become reversed; the
    # dashboard sidebar and LCD show the current class and score normally.


def calculate_upper_body_metrics(nose: Any, left_ear: Any, right_ear: Any, left_shoulder: Any, right_shoulder: Any) -> dict[str, float]:
    """Score the fixed frontal desk-camera view from 2-D upper-body points.

    This profile deliberately uses only image-plane locations of the nose,
    ears and shoulders. Relative MediaPipe Z varies when this camera is a
    little off-centre, so it must not create a large false shoulder angle.
    ``torso`` remains an upper-body alignment indicator, not spinal curvature.
    """
    mid_ear_x = (float(left_ear.x) + float(right_ear.x)) / 2
    mid_ear_y = (float(left_ear.y) + float(right_ear.y)) / 2
    mid_shoulder_x = (float(left_shoulder.x) + float(right_shoulder.x)) / 2
    mid_shoulder_y = (float(left_shoulder.y) + float(right_shoulder.y)) / 2

    head_x = (float(nose.x) + mid_ear_x) / 2
    head_y = (float(nose.y) + mid_ear_y) / 2
    vertical = max(0.001, mid_shoulder_y - head_y)
    degrees = 180.0 / math.pi

    # Front view: assess only head/neck side alignment and head roll. Forward
    # head posture requires a side view, not an uncalibrated Z estimate.
    head_offset = math.atan2(abs(head_x - mid_shoulder_x), vertical) * degrees
    head_roll = math.atan2(abs(float(left_ear.y) - float(right_ear.y)), max(0.001, abs(float(left_ear.x) - float(right_ear.x)))) * degrees
    neck = math.hypot(head_offset, head_roll)

    # Shoulder height is reliable in this fixed frontal view. Do not infer
    # shoulder depth: it was the source of 50-60 degree false readings.
    shoulder_tilt = math.atan2(abs(float(left_shoulder.y) - float(right_shoulder.y)), max(0.001, abs(float(left_shoulder.x) - float(right_shoulder.x)))) * degrees
    shoulders = shoulder_tilt
    torso = 0.0
    score = score_frontal_desk_metrics(neck, shoulders, torso)
    return {
        "neck": round(neck, 1),
        "shoulders": round(shoulders, 1),
        "torso": round(torso, 1),
        "score": round(score, 1),
    }


def score_frontal_desk_metrics(neck: float, shoulders: float, forward_lean: float) -> float:
    """Score a frontal desk pose, with optional calibrated forward-lean trend."""
    neck_penalty = min(30.0, max(0.0, neck - 12.0) * 1.2)
    shoulder_penalty = min(30.0, max(0.0, shoulders - 10.0) * 1.0)
    lean_penalty = min(25.0, max(0.0, forward_lean - 8.0) * 1.0)
    return round(max(0.0, min(100.0, 100.0 - neck_penalty - shoulder_penalty - lean_penalty)), 1)


class MediaPipePoseDetector:
    """Wrapper for MediaPipe Pose landmarker matching frontend posture scoring."""

    def __init__(self, model_path: Path) -> None:
        import mediapipe as mp  # type: ignore

        if not model_path.is_file():
            raise FileNotFoundError(f"Pose Landmarker Full model not found: {model_path}")
        self.mp = mp
        self._last_timestamp_ms = -1
        self._forward_lean_baseline: float | None = None
        self._forward_lean_samples: deque[float] = deque(maxlen=20)
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
        if len(landmarks) < 25:
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
        visible_points = [
            point
            for point in landmarks
            if getattr(point, "visibility", 1.0) >= 0.45 and 0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0
        ]
        person_box: dict[str, float] | None = None
        if len(visible_points) >= 5:
            min_x = min(point.x for point in visible_points)
            max_x = max(point.x for point in visible_points)
            min_y = min(point.y for point in visible_points)
            max_y = max(point.y for point in visible_points)
            margin_x = max(0.04, (max_x - min_x) * 0.12)
            margin_y = max(0.04, (max_y - min_y) * 0.12)
            person_box = {
                "left": max(0.0, min_x - margin_x),
                "top": max(0.0, min_y - margin_y),
                "right": min(1.0, max_x + margin_x),
                "bottom": min(1.0, max_y + margin_y),
            }

        nose = landmarks[0]
        le = landmarks[7]
        re = landmarks[8]
        ls = landmarks[11]
        rs = landmarks[12]

        # Upper-body scoring deliberately does not require hips or legs: a
        # desk often blocks them in a front-facing sitting camera view.
        for pt in [nose, le, re, ls, rs]:
            if getattr(pt, "visibility", 1.0) < 0.45:
                return {"landmarks": overlay_landmarks}
        metrics = calculate_upper_body_metrics(nose, le, re, ls, rs)
        metrics["torso"] = self._forward_lean_proxy(metrics, nose, le, re, ls, rs)
        metrics["score"] = score_frontal_desk_metrics(metrics["neck"], metrics["shoulders"], metrics["torso"])
        return {
            **metrics,
            "landmarks": overlay_landmarks,
            "person_box": person_box,
        }

    def _forward_lean_proxy(self, metrics: dict[str, float], nose: Any, left_ear: Any, right_ear: Any, left_shoulder: Any, right_shoulder: Any) -> float:
        """Return forward-lean change relative to this person's neutral pose.

        The first twenty stable, aligned frames form a per-session reference.
        Only the *change* in relative depth from that reference is used, never
        raw Z, so a slightly diagonal camera cannot create a false slouch.
        """
        head_z = (float(getattr(nose, "z", 0.0)) + float(getattr(left_ear, "z", 0.0)) + float(getattr(right_ear, "z", 0.0))) / 3
        shoulder_z = (float(getattr(left_shoulder, "z", 0.0)) + float(getattr(right_shoulder, "z", 0.0))) / 2
        relative_depth = shoulder_z - head_z  # positive when the head moves closer than the shoulders
        head_y = (float(nose.y) + float(left_ear.y) + float(right_ear.y)) / 3
        shoulder_y = (float(left_shoulder.y) + float(right_shoulder.y)) / 2
        vertical = max(0.001, shoulder_y - head_y)

        if self._forward_lean_baseline is None:
            # Ask the user to sit naturally upright after a restart; only use
            # frames without an obvious 2-D lean as the neutral reference.
            if metrics["neck"] <= 12.0 and metrics["shoulders"] <= 10.0:
                self._forward_lean_samples.append(relative_depth)
            if len(self._forward_lean_samples) == self._forward_lean_samples.maxlen:
                self._forward_lean_baseline = sorted(self._forward_lean_samples)[len(self._forward_lean_samples) // 2]
                logger.info("calibrated frontal forward-lean baseline; monitoring relative change")
            return 0.0

        change_toward_camera = max(0.0, relative_depth - self._forward_lean_baseline)
        return round(math.atan2(change_toward_camera, vertical) * 180.0 / math.pi, 1)

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
    global _pose_detector, _detector_model_path, _posture_classifier, _classifier_model_path
    global _failed_classifier_model_path, _last_analysis_at, _pose_visible
    if _pose_detector is not None:
        _pose_detector.close()
    _pose_detector = None
    _detector_model_path = None
    if _posture_classifier is not None:
        _posture_classifier.close()
    _posture_classifier = None
    _classifier_model_path = None
    _failed_classifier_model_path = None
    _last_analysis_at = 0.0
    _pose_visible = False
    _overlay_smoother.reset()
    _metric_smoother.reset()


def get_posture_classifier(config: dict[str, Any]) -> Any | None:
    """Return the optional ONNX classifier without ever interrupting Pose."""
    global _posture_classifier, _classifier_model_path, _failed_classifier_model_path
    settings = config.get("posture_classifier", {})
    if not settings.get("enabled", True):
        return None
    model_value = settings.get("model")
    if not model_value:
        return None
    model_path = Path(str(model_value)).resolve()
    if _failed_classifier_model_path == model_path:
        return None
    if _posture_classifier is not None and _classifier_model_path == model_path:
        return _posture_classifier
    if _posture_classifier is not None:
        _posture_classifier.close()
        _posture_classifier = None
    try:
        from client.posture_classifier import OnnxPostureClassifier

        _posture_classifier = OnnxPostureClassifier(model_path)
        _classifier_model_path = model_path
        logger.info("initialized Kanden ONNX posture classifier: %s", model_path)
        return _posture_classifier
    except Exception as exc:
        _failed_classifier_model_path = model_path
        logger.error("Kanden posture classifier is unavailable; using MediaPipe score fallback: %s", exc)
        return None


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
            logger.debug("pose detected but required head/shoulder landmarks are not visible; sending overlay without a score")
            if frame_overlay_callback is not None:
                frame_overlay_callback(landmarks, None)
            else:
                draw_pose_overlay(frame, landmarks, min_visibility=min_visibility)
            if pose_callback is not None:
                pose_callback({}, landmarks)
            return
        person_box = result.pop("person_box", None)
        score_source = str(detection.get("score_source", "upper_body")).lower()
        classifier = get_posture_classifier(config) if score_source == "image_classifier" else None
        if classifier is not None:
            try:
                classification = classifier.classify(
                    frame,
                    color_space,
                    interval=float(config.get("posture_classifier", {}).get("interval", 0.5)),
                    person_box=person_box,
                )
                result.update(classification)
                confidence = float(classification["posture_confidence"])
                min_confidence = float(config.get("posture_classifier", {}).get("min_confidence", 0.65))
                if confidence >= min_confidence:
                    from client.posture_classifier import score_for_label

                    result["score"] = score_for_label(str(classification["posture_label"]))
                    result["posture_ai_used"] = True
                else:
                    result["posture_ai_used"] = False
                    logger.debug(
                        "Kanden classifier confidence %.0f%% is below %.0f%%; using MediaPipe score fallback",
                        confidence * 100,
                        min_confidence * 100,
                    )
            except Exception as exc:
                logger.warning("Kanden posture classifier failed for this frame; using MediaPipe score fallback: %s", exc)

        metrics = _metric_smoother.update(result, metric_alpha)
        for key in ("posture_label", "posture_confidence", "posture_ai_used"):
            if key in result:
                metrics[key] = result[key]
        if frame_overlay_callback is not None:
            frame_overlay_callback(landmarks, metrics)
        else:
            draw_pose_overlay(frame, landmarks, metrics, min_visibility=min_visibility)
        logger.debug("detected metrics: score=%s, neck=%s°, shoulders=%s°, torso=%s°",
                     metrics["score"], metrics["neck"], metrics["shoulders"], metrics["torso"])
        uploader.send_sample({key: metrics[key] for key in METRIC_KEYS})

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
