"""Small, optional client for Roboflow hosted posture models."""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class RoboflowPostureClient:
    """Call a Roboflow Object Detection model at a bounded rate.

    The API key is deliberately read from an environment variable instead of
    config.yaml, which keeps it out of the repository and ordinary backups.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.model_id = str(config.get("model_id", "sitting-posture-detection-3933f/2")).strip()
        self.interval = max(0.5, float(config.get("interval", 1.0)))
        self.min_confidence = min(1.0, max(0.0, float(config.get("confidence", 0.6))))
        self.timeout = max(1.0, float(config.get("timeout", 8.0)))
        self.api_key_env = str(config.get("api_key_env", "ROBOFLOW_API_KEY")).strip()
        self.api_key = os.environ.get(self.api_key_env, "").strip()
        self._last_attempt_at = 0.0
        self._last_warning_at = 0.0
        self._last_logged_label: str | None = None

        if self.enabled and not self.api_key:
            logger.warning("Roboflow is enabled but %s is not set; remote posture AI is disabled", self.api_key_env)
            self.enabled = False

    def infer_if_due(self, frame: Any, color_space: str = "rgb") -> dict[str, Any] | None:
        """Return the most confident posture prediction, or None when skipped."""
        if not self.enabled:
            return None
        now = time.monotonic()
        if now - self._last_attempt_at < self.interval:
            return None
        self._last_attempt_at = now

        try:
            image_b64 = self._encode_frame(frame, color_space)
            response = requests.post(
                f"https://detect.roboflow.com/{self.model_id}",
                params={"api_key": self.api_key},
                data=image_b64,
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = self._select_prediction(response.json())
            if result is not None and result["label"] != self._last_logged_label:
                logger.info(
                    "Roboflow posture classification: %s (%.0f%%)",
                    result["label"],
                    result["confidence"] * 100,
                )
                self._last_logged_label = result["label"]
            return result
        except (ValueError, requests.RequestException) as exc:
            # A cloud outage must never stop the local MediaPipe pipeline.
            if now - self._last_warning_at >= 30:
                logger.warning("Roboflow posture inference failed: %s", exc)
                self._last_warning_at = now
            return None

    def _encode_frame(self, frame: Any, color_space: str) -> bytes:
        import cv2  # type: ignore

        if not hasattr(frame, "shape"):
            raise ValueError("Roboflow inference requires an image frame")
        image = frame
        if color_space == "rgb":
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        ok, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if not ok:
            raise ValueError("could not encode camera frame as JPEG")
        return base64.b64encode(jpeg.tobytes())

    def _select_prediction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        best: tuple[float, str] | None = None
        for item in payload.get("predictions", []):
            if not isinstance(item, dict):
                continue
            label = item.get("class")
            try:
                confidence = float(item.get("confidence", 0))
            except (TypeError, ValueError):
                continue
            if not isinstance(label, str) or confidence < self.min_confidence:
                continue
            if best is None or confidence > best[0]:
                best = (confidence, label)
        if best is None:
            return None
        return {
            "label": best[1],
            "confidence": round(best[0], 4),
            "model": self.model_id,
        }
