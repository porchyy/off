"""Camera capture helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def open_camera(config: dict) -> Any:
    """Open the configured camera. Returns an object with read()/release()."""
    import cv2  # type: ignore

    index = int(config.get("index", 0))
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(config.get("width", 640)))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config.get("height", 480)))
    flip = int(config.get("flip", 0))
    if not cap.isOpened():
        raise RuntimeError(f"failed to open camera at index {index}")
    logger.info("opened camera index=%s width=%s height=%s flip=%s", index, config.get("width"), config.get("height"), flip)
    cap._postureai_flip = flip  # type: ignore[attr-defined]
    return cap
