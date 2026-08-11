"""Local YOLOv5 sitting-posture detector.

Uses the MIT-licensed ``small640.pt`` checkpoint from
itakurah/Sitting-Posture-Detection-YOLOv5.  The model has two classes:
``sitting_good`` (0) and ``sitting_bad`` (1).
"""

from __future__ import annotations

import logging
import time
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_URL = (
    "https://raw.githubusercontent.com/itakurah/Sitting-Posture-Detection-YOLOv5/"
    "main/data/inference_models/small640.pt"
)

_detector: YoloV5PostureDetector | None = None
_detector_path: Path | None = None
_last_analysis_at = 0.0


class YoloV5PostureDetector:
    """Run the upstream lateral sitting-posture model on local Pi frames."""

    def __init__(self, model_path: Path, config: dict[str, Any]) -> None:
        try:
            import yolov5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "YOLOv5 runtime is unavailable; run ./setup-yolov5-pi.sh first"
            ) from exc

        if not model_path.is_file():
            self._download_model(model_path, str(config.get("model_url", DEFAULT_MODEL_URL)))
        self.model = yolov5.load(str(model_path), device="cpu")
        self.model.conf = min(1.0, max(0.05, float(config.get("confidence", 0.5))))
        self.model.iou = min(1.0, max(0.05, float(config.get("iou", 0.5))))
        self.model.classes = [0, 1]
        self.model.max_det = 1
        self.model.agnostic = False
        self.model.multi_label = False
        self.model.amp = False
        logger.info("YOLOv5 sitting-posture model ready: %s", model_path)

    @staticmethod
    def _download_model(model_path: Path, model_url: str) -> None:
        if not model_url.startswith("https://"):
            raise ValueError("detection.model_url must use https://")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = model_path.with_suffix(f"{model_path.suffix}.download")
        logger.info("downloading YOLOv5 sitting-posture model from upstream repository")
        try:
            urllib.request.urlretrieve(model_url, temporary_path)
            temporary_path.replace(model_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"could not download YOLOv5 model: {exc}") from exc

    @staticmethod
    def _select_prediction(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        best: dict[str, Any] | None = None
        for row in rows:
            try:
                confidence = float(row.get("confidence", 0))
                class_id = int(row.get("class", -1))
            except (TypeError, ValueError):
                continue
            if class_id not in {0, 1}:
                continue
            if best is None or confidence > best["confidence"]:
                best = {
                    "class_id": class_id,
                    "confidence": confidence,
                    "bbox": {
                        "x1": int(float(row.get("xmin", 0))),
                        "y1": int(float(row.get("ymin", 0))),
                        "x2": int(float(row.get("xmax", 0))),
                        "y2": int(float(row.get("ymax", 0))),
                    },
                }
        if best is None:
            return None
        good = best["class_id"] == 0
        return {
            "score": 100.0 if good else 0.0,
            # The backend keeps these numeric fields for historical charts.
            # YOLOv5 classifies the whole posture and does not provide angles.
            "neck": 0.0,
            "shoulders": 0.0,
            "torso": 0.0,
            "posture": "sitting_good" if good else "sitting_bad",
            "confidence": round(best["confidence"], 4),
            "bbox": best["bbox"],
            "detector": "yolov5",
        }

    def calculate_metrics(self, frame: Any, color_space: str = "bgr") -> dict[str, Any] | None:
        if color_space not in {"bgr", "rgb"}:
            raise ValueError(f"unsupported camera color space: {color_space}")
        image = frame
        if color_space == "rgb":
            import cv2  # type: ignore

            image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        results = self.model(image)
        rows = results.pandas().xyxy[0].to_dict(orient="records")
        metrics = self._select_prediction(rows)
        if metrics is not None:
            height, width = frame.shape[:2]
            # The dashboard needs the original frame dimensions to draw this
            # upstream YOLOv5 bounding box over its mirrored WebRTC preview.
            metrics["frame_width"] = int(width)
            metrics["frame_height"] = int(height)
        return metrics


def get_detector(model_path: str | Path, config: dict[str, Any]) -> YoloV5PostureDetector:
    global _detector, _detector_path
    resolved_path = Path(model_path).resolve()
    if _detector is None or _detector_path != resolved_path:
        _detector = YoloV5PostureDetector(resolved_path, config)
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
    """Classify the current frame and preserve the existing alert pipeline."""
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
        if frame_overlay_callback is not None:
            frame_overlay_callback([], None)
        if detection_callback is not None:
            detection_callback({})
        return

    logger.info(
        "YOLOv5 posture: %s (%.0f%% confidence)",
        metrics["posture"],
        metrics["confidence"] * 100,
    )
    uploader.send_sample(metrics)
    if lcd_display is not None:
        lcd_display.show_metrics(metrics)
    if alert_controller is not None:
        alert_controller.update(metrics)
    if frame_overlay_callback is not None:
        frame_overlay_callback([], metrics)
    if detection_callback is not None:
        detection_callback(metrics)
