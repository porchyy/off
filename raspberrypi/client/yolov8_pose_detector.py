"""Front-view sitting-posture analysis with Ultralytics YOLOv8-Pose.

The keypoint and scoring approach is adapted for PostureAI from the
MIT-licensed aaron888hacker/-yolov8- project.  It uses the COCO face,
shoulder and hip keypoints from ``yolov8n-pose.pt`` instead of a fixed
good/bad image classifier, so a front-facing Pi Camera can be calibrated
against the user's visible alignment.
"""

from __future__ import annotations

import logging
import math
import time
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.pt"

_detector: YoloV8PoseDetector | None = None
_detector_path: Path | None = None
_last_analysis_at = 0.0


class YoloV8PoseDetector:
    """Run YOLOv8-Pose and score front-view head, shoulders and torso."""

    def __init__(self, model_path: Path, config: dict[str, Any]) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "YOLOv8-Pose runtime is unavailable; run ./setup-yolov8-pose-pi.sh first"
            ) from exc

        if not model_path.is_file():
            self._download_model(model_path, str(config.get("model_url", DEFAULT_MODEL_URL)))
        self.model = YOLO(str(model_path))
        self.confidence = min(1.0, max(0.05, float(config.get("confidence", 0.35))))
        self.iou = min(1.0, max(0.05, float(config.get("iou", 0.5))))
        logger.info("YOLOv8-Pose front-view model ready: %s", model_path)

    @staticmethod
    def _download_model(model_path: Path, model_url: str) -> None:
        if not model_url.startswith("https://"):
            raise ValueError("detection.model_url must use https://")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = model_path.with_suffix(f"{model_path.suffix}.download")
        logger.info("downloading YOLOv8-Pose model")
        try:
            urllib.request.urlretrieve(model_url, temporary_path)
            temporary_path.replace(model_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"could not download YOLOv8-Pose model: {exc}") from exc

    @staticmethod
    def _point(keypoints: list[list[float]], index: int) -> tuple[float, float, float] | None:
        if index >= len(keypoints) or len(keypoints[index]) < 3:
            return None
        x, y, confidence = (float(value) for value in keypoints[index][:3])
        if confidence < 0.35 or x <= 0 or y <= 0:
            return None
        return x, y, confidence

    @classmethod
    def _analyze_keypoints(
        cls,
        keypoints: list[list[float]],
        box: list[float],
        box_confidence: float,
        frame_width: int,
        frame_height: int,
    ) -> dict[str, Any] | None:
        # COCO keypoints: ears 3/4, shoulders 5/6, hips 11/12.
        left_ear = cls._point(keypoints, 3)
        right_ear = cls._point(keypoints, 4)
        left_shoulder = cls._point(keypoints, 5)
        right_shoulder = cls._point(keypoints, 6)
        left_hip = cls._point(keypoints, 11)
        right_hip = cls._point(keypoints, 12)
        required = (left_ear, right_ear, left_shoulder, right_shoulder, left_hip, right_hip)
        x1, y1, x2, y2 = (int(max(0, value)) for value in box[:4])
        preview = {
            # Still send a visible YOLOv8-Pose frame when the person is only
            # partly in view. This matches the source project's visual
            # feedback while keeping incomplete poses out of scoring/alerts.
            "posture": "align_camera",
            "confidence": round(float(box_confidence), 4),
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "keypoints": [
                {"index": index, "x": round(float(point[0]), 1), "y": round(float(point[1]), 1), "visibility": round(float(point[2]), 4)}
                for index, point in enumerate(keypoints)
                if len(point) >= 3
            ],
            "frame_width": int(frame_width),
            "frame_height": int(frame_height),
            "detector": "yolov8_pose",
            "scorable": False,
        }
        if any(point is None for point in required):
            return preview

        le, re, ls, rs, lh, rh = required  # type: ignore[misc]
        head_x, head_y = (le[0] + re[0]) / 2, (le[1] + re[1]) / 2
        shoulder_x, shoulder_y = (ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2
        hip_x, hip_y = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        head_to_shoulder = shoulder_y - head_y
        shoulder_to_hip = hip_y - shoulder_y
        shoulder_width = abs(ls[0] - rs[0])
        if head_to_shoulder <= 1 or shoulder_to_hip <= 1 or shoulder_width <= 1:
            return preview

        # Front-view metrics: lateral head drift, shoulder height imbalance,
        # and lateral torso lean. These are stable 2D measures for one camera.
        neck = math.degrees(math.atan2(abs(head_x - shoulder_x), head_to_shoulder))
        shoulders = math.degrees(math.atan2(abs(ls[1] - rs[1]), shoulder_width))
        torso = math.degrees(math.atan2(abs(shoulder_x - hip_x), shoulder_to_hip))
        score = 100 - max(0.0, neck - 6) * 3.0 - max(0.0, shoulders - 4) * 3.0 - max(0.0, torso - 5) * 2.5
        score = round(max(0.0, min(100.0, score)), 1)
        posture = "perfect" if score >= 90 else "good" if score >= 70 else "bad"
        visible_confidence = sum(point[2] for point in required) / len(required)
        preview.update({
            "score": score,
            "neck": round(neck, 1),
            "shoulders": round(shoulders, 1),
            "torso": round(torso, 1),
            "posture": posture,
            "confidence": round(min(float(box_confidence), visible_confidence), 4),
            "scorable": True,
        })
        return preview

    def calculate_metrics(self, frame: Any, color_space: str = "bgr") -> dict[str, Any] | None:
        if color_space not in {"bgr", "rgb"}:
            raise ValueError(f"unsupported camera color space: {color_space}")
        image = frame
        if color_space == "rgb":
            import cv2  # type: ignore

            image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        results = self.model.predict(image, conf=self.confidence, iou=self.iou, device="cpu", imgsz=640, verbose=False, max_det=1)
        if not results:
            return None
        result = results[0]
        if result.boxes is None or result.keypoints is None or len(result.boxes) == 0:
            return None
        boxes = result.boxes.xyxy.cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        best_index = max(range(len(boxes)), key=lambda index: (boxes[index][2] - boxes[index][0]) * (boxes[index][3] - boxes[index][1]))
        keypoints = result.keypoints.data[best_index].cpu().tolist()
        height, width = frame.shape[:2]
        return self._analyze_keypoints(keypoints, boxes[best_index], confidences[best_index], width, height)


def get_detector(model_path: str | Path, config: dict[str, Any]) -> YoloV8PoseDetector:
    global _detector, _detector_path
    resolved_path = Path(model_path).resolve()
    if _detector is None or _detector_path != resolved_path:
        _detector = YoloV8PoseDetector(resolved_path, config)
        _detector_path = resolved_path
    return _detector


def close_detector() -> None:
    global _detector, _detector_path, _last_analysis_at
    _detector = None
    _detector_path = None
    _last_analysis_at = 0.0


def process_live_frame(
    frame: Any,
    config: dict[str, Any],
    uploader: Any,
    alert_controller: Any | None = None,
    color_space: str = "rgb",
    detection_callback: Any | None = None,
    frame_overlay_callback: Any | None = None,
    lcd_display: Any | None = None,
) -> None:
    """Analyze a front-view frame without changing the existing alert flow."""
    global _last_analysis_at
    detection = config.get("detection", {})
    now = time.monotonic()
    if now - _last_analysis_at < max(0.0, float(detection.get("interval", 0.5))):
        return
    _last_analysis_at = now

    detector = get_detector(detection["model"], detection)
    metrics = detector.calculate_metrics(frame, color_space)
    if metrics is None:
        if alert_controller is not None:
            alert_controller.clear_posture()
        if lcd_display is not None:
            lcd_display.show_waiting_for_pose()
        if detection_callback is not None:
            detection_callback({})
        return

    if not metrics.get("scorable", False):
        logger.info("YOLOv8-Pose person detected; waiting for ears, shoulders and hips to score")
        if alert_controller is not None:
            alert_controller.clear_posture()
        if lcd_display is not None:
            lcd_display.show_waiting_for_pose()
        if detection_callback is not None:
            detection_callback(metrics)
        return

    logger.info("YOLOv8-Pose posture: %s (score %.1f, %.0f%% confidence)", metrics["posture"], metrics["score"], metrics["confidence"] * 100)
    uploader.send_sample(metrics)
    if lcd_display is not None:
        lcd_display.show_metrics(metrics)
    if alert_controller is not None:
        alert_controller.update(metrics)
    if detection_callback is not None:
        detection_callback(metrics)
