"""ONNX image classifier for the Kanden sitting-posture model.

MediaPipe remains responsible for locating the person and drawing the
skeleton.  This module only classifies the current camera image once a usable
pose is visible, so an empty room is never treated as a bad posture.
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CLASS_LABELS = ("good", "slouch", "chin_rest", "stretch")
# These values keep the existing 0-100 dashboard, alert, LED and LCD pipeline
# while making the learned class—not a hand-tuned angle formula—the decision.
SCORES_BY_LABEL = {
    "good": 100.0,
    "stretch": 80.0,
    "slouch": 30.0,
    "chin_rest": 15.0,
}


def score_for_label(label: str) -> float:
    """Map a recognised class to the existing 0-100 posture score."""
    return SCORES_BY_LABEL.get(label, 50.0)


class OnnxPostureClassifier:
    """Run the published ResNet18 posture classifier on Pi CPU."""

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"posture classifier model not found: {model_path}")
        try:
            import onnxruntime as ort  # type: ignore
        except ImportError as exc:
            raise RuntimeError("onnxruntime is not installed") from exc

        self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        inputs = self._session.get_inputs()
        outputs = self._session.get_outputs()
        if len(inputs) != 1 or not outputs:
            raise RuntimeError("unexpected ONNX posture classifier input/output signature")
        self._input_name = inputs[0].name
        self._output_name = outputs[0].name
        self._last_run_at = -math.inf
        self._last_result: dict[str, Any] | None = None

    @staticmethod
    def _preprocess(frame: Any, color_space: str) -> Any:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        if color_space not in {"bgr", "rgb"}:
            raise ValueError(f"unsupported camera color space: {color_space}")
        rgb = frame if color_space == "rgb" else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
        tensor = image.astype(np.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
        return ((tensor - mean) / std)[np.newaxis, ...]

    def classify(self, frame: Any, color_space: str, *, interval: float) -> dict[str, Any]:
        """Return a cached result between inference runs to protect Pi FPS."""
        now = time.monotonic()
        if self._last_result is not None and now - self._last_run_at < interval:
            return dict(self._last_result)

        import numpy as np  # type: ignore

        logits = self._session.run([self._output_name], {self._input_name: self._preprocess(frame, color_space)})[0]
        values = np.asarray(logits, dtype=np.float32).reshape(-1)
        if values.size != len(CLASS_LABELS):
            raise RuntimeError(f"unexpected posture classifier output length: {values.size}")
        exp = np.exp(values - np.max(values))
        probabilities = exp / exp.sum()
        index = int(np.argmax(probabilities))
        label = CLASS_LABELS[index]
        self._last_result = {
            "posture_label": label,
            "posture_confidence": round(float(probabilities[index]), 4),
        }
        self._last_run_at = now
        return dict(self._last_result)

    def close(self) -> None:
        # onnxruntime releases its native session when references are dropped;
        # clearing the attribute makes that deterministic for service restarts.
        self._session = None
