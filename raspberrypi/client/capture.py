"""Camera capture helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def open_camera(config: dict) -> Any:
    """Open the configured camera with retry logic. Returns an object with read()/release()."""
    import cv2  # type: ignore

    index = int(config.get("index", 0))
    width = int(config.get("width", 640))
    height = int(config.get("height", 480))
    flip = int(config.get("flip", 0))
    retries = int(config.get("retries", 3))

    cap = None
    for attempt in range(1, retries + 1):
        cap = cv2.VideoCapture(index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if cap.isOpened():
            logger.info("opened camera index=%s width=%s height=%s flip=%s (attempt %s)", index, width, height, flip, attempt)
            cap._postureai_flip = flip  # type: ignore[attr-defined]
            return cap
        logger.warning("failed to open camera index=%s on attempt %s/%s", index, attempt, retries)
        if cap:
            cap.release()

    raise RuntimeError(f"failed to open camera at index {index} after {retries} attempts")

