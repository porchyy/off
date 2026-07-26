"""Pose detection + scoring module for Raspberry Pi using MediaPipe."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

_pose_detector = None


class MediaPipePoseDetector:
    """Wrapper for MediaPipe Pose landmarker matching frontend posture scoring."""

    def __init__(self) -> None:
        import mediapipe as mp  # type: ignore

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Lite model for fast inference on Raspberry Pi
            smooth_landmarks=True,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45,
        )

    def calculate_metrics(self, frame: Any) -> dict[str, float] | None:
        import cv2  # type: ignore

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if not results.pose_landmarks:
            return None

        landmarks = results.pose_landmarks.landmark
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


def get_detector() -> Any:
    global _pose_detector
    if _pose_detector is None:
        try:
            _pose_detector = MediaPipePoseDetector()
            logger.info("initialized MediaPipe Pose detector (model_complexity=0)")
        except Exception as exc:
            logger.warning("could not initialize MediaPipe (%s), falling back to demo metrics", exc)
            _pose_detector = "fallback"
    return _pose_detector


def run_detection_cycle(camera: Any, config: dict, uploader: Any) -> None:
    """Read one frame, calculate pose metrics, and forward to backend."""
    import cv2  # type: ignore

    ok, frame = camera.read()
    if not ok or frame is None:
        logger.warning("failed to read frame from camera")
        return

    flip = getattr(camera, "_postureai_flip", 0)
    if flip:
        frame = cv2.flip(frame, flip)

    detector = get_detector()
    if detector != "fallback":
        metrics = detector.calculate_metrics(frame)
    else:
        metrics = _placeholder_metrics()

    if metrics:
        logger.debug("detected metrics: score=%s, neck=%s°, shoulders=%s%%, torso=%s°",
                     metrics["score"], metrics["neck"], metrics["shoulders"], metrics["torso"])
        uploader.send_sample(metrics)

        # Check risk threshold for alert trigger
        threshold = config.get("risk", {}).get("threshold", 60)
        if metrics["score"] < threshold:
            logger.info("low posture score detected (%s < %s), sending alert", metrics["score"], threshold)
            uploader.send_alert({
                "severity": "risk",
                "message": f"ตรวจพบท่านั่งที่ควรปรับ (คะแนน {metrics['score']})"
            })
    else:
        logger.debug("no pose landmarks detected in frame")


def _placeholder_metrics() -> dict[str, float]:
    return {"score": 75.0, "neck": 15.0, "shoulders": 10.0, "torso": 5.0}
