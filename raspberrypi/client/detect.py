"""Pose detection + scoring module for Raspberry Pi using MediaPipe."""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_pose_detector: MediaPipePoseDetector | None = None
_detector_model_path: Path | None = None


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

    def calculate_metrics(self, frame: Any, color_space: str = "bgr") -> dict[str, float] | None:
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

        nose = landmarks[0]
        ls = landmarks[11]
        rs = landmarks[12]
        lh = landmarks[23]
        rh = landmarks[24]

        # Ensure key landmarks are visible enough
        for pt in [nose, ls, rs, lh, rh]:
            if getattr(pt, "visibility", 1.0) < 0.45:
                return None

        sh_x = (ls.x + rs.x) / 2.0
        sh_y = (ls.y + rs.y) / 2.0
        hip_x = (lh.x + rh.x) / 2.0
        hip_y = (lh.y + rh.y) / 2.0

        neck = abs(math.atan2(nose.x - sh_x, max(0.001, sh_y - nose.y)) * 180.0 / math.pi)
        shoulders = abs(ls.y - rs.y) * 100.0
        torso = abs(math.atan2(sh_x - hip_x, max(0.001, hip_y - sh_y)) * 180.0 / math.pi)

        score = max(0.0, min(100.0, 100.0 - max(0.0, neck - 12.0) * 2.3 - shoulders * 1.4 - max(0.0, torso - 7.0) * 2.0))

        return {
            "score": round(score, 1),
            "neck": round(neck, 1),
            "shoulders": round(shoulders, 1),
            "torso": round(torso, 1),
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
    global _pose_detector, _detector_model_path
    if _pose_detector is not None:
        _pose_detector.close()
    _pose_detector = None
    _detector_model_path = None


def run_detection_cycle(camera: Any, config: dict, uploader: Any, alert_controller: Any | None = None) -> None:
    """Read one frame, calculate pose metrics, and forward to backend."""
    import cv2  # type: ignore

    ok, frame = camera.read()
    if not ok or frame is None:
        logger.warning("failed to read frame from camera")
        return

    flip = getattr(camera, "flip", 0)
    if flip:
        frame = cv2.flip(frame, flip)

    detector = get_detector(config["detection"]["model"])
    metrics = detector.calculate_metrics(frame, getattr(camera, "color_space", "bgr"))

    if metrics:
        logger.debug("detected metrics: score=%s, neck=%s°, shoulders=%s%%, torso=%s°",
                     metrics["score"], metrics["neck"], metrics["shoulders"], metrics["torso"])
        uploader.send_sample(metrics)

        if alert_controller is not None:
            alert_controller.update(metrics)
    else:
        logger.debug("no pose landmarks detected in frame")
