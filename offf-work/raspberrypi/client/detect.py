"""Pose detection + scoring.

Skeleton — full port of frontend/app.js MediaPipe logic จะตามมา
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_detection_cycle(camera: Any, config: dict, uploader: Any) -> None:
    """Read one frame, score it, and forward to the backend."""
    import cv2  # type: ignore

    ok, frame = camera.read()
    if not ok or frame is None:
        logger.warning("failed to read frame")
        return
    flip = getattr(camera, "_postureai_flip", 0)
    if flip:
        frame = cv2.flip(frame, flip)

    # TODO: MediaPipe Pose processing here.
    score, neck, shoulders, torso = _placeholder_metrics(frame)
    uploader.send_sample({
        "score": score,
        "neck": neck,
        "shoulders": shoulders,
        "torso": torso,
    })


def _placeholder_metrics(frame: Any) -> tuple[float, float, float, float]:
    """Return deterministic placeholder metrics so the upload loop has data to send.

    Replace with real MediaPipe scoring (see frontend/app.js) when wiring is done.
    """
    return 75.0, 15.0, 10.0, 5.0
