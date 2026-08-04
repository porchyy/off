"""Camera capture helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Camera:
    """Small common interface for OpenCV and Picamera2 cameras."""

    def __init__(self, device: Any, backend: str, flip: int = 0, color_space: str = "bgr") -> None:
        self.device = device
        self.backend = backend
        self.flip = flip
        self.color_space = color_space

    def read(self) -> tuple[bool, Any]:
        if self.backend == "picamera2":
            frame = self.device.capture_array("main")
            return frame is not None, frame
        return self.device.read()

    def release(self) -> None:
        if self.backend == "picamera2":
            self.device.stop()
            self.device.close()
        else:
            self.device.release()


def _open_picamera2(width: int, height: int, flip: int) -> Camera:
    from picamera2 import Picamera2  # type: ignore

    camera = Picamera2()
    camera.configure(camera.create_preview_configuration(
        main={"size": (width, height), "format": "RGB888"}
    ))
    camera.start()
    time.sleep(1.0)  # Allow auto-exposure to settle.
    # Picamera2 returns RGB888 here.  Keep that information so the detector
    # does not incorrectly treat it as OpenCV's usual BGR frame.
    return Camera(camera, "picamera2", flip, color_space="rgb")


def _camera_indices(index: Any) -> list[int]:
    if index is None or str(index).strip().lower() in {"", "auto"}:
        devices = sorted(Path("/dev").glob("video[0-9]*"))
        indices = []
        for device in devices:
            suffix = device.name.removeprefix("video")
            if suffix.isdigit():
                indices.append(int(suffix))
        return indices
    if isinstance(index, (list, tuple)):
        return [int(value) for value in index]
    if isinstance(index, str) and "," in index:
        return [int(value.strip()) for value in index.split(",") if value.strip()]
    return [int(index)]


def _open_opencv(index: int, width: int, height: int, flip: int) -> Camera:
    import cv2  # type: ignore

    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"OpenCV could not open /dev/video{index}")
    return Camera(cap, "opencv", flip, color_space="bgr")


def open_camera(config: dict) -> Camera:
    """Open Pi Camera or USB camera with retry logic."""

    index_config = config.get("index", "auto")
    indices = _camera_indices(index_config)
    width = int(config.get("width", 640))
    height = int(config.get("height", 480))
    flip = int(config.get("flip", 0))
    retries = int(config.get("retries", 3))
    backend = str(config.get("backend", "auto")).lower()

    if backend not in {"auto", "picamera2", "opencv"}:
        raise ValueError("camera.backend must be auto, picamera2, or opencv")

    for attempt in range(1, retries + 1):
        errors = []
        if backend in {"auto", "picamera2"}:
            try:
                camera = _open_picamera2(width, height, flip)
                logger.info("opened Pi Camera via Picamera2 (%sx%s)", width, height)
                return camera
            except Exception as exc:
                errors.append(f"Picamera2: {exc}")
        if backend in {"auto", "opencv"}:
            if not indices:
                errors.append("OpenCV: no /dev/video* devices found; connect a USB camera or set camera.backend=picamera2")
            for index in indices:
                try:
                    camera = _open_opencv(index, width, height, flip)
                    logger.info("opened USB camera index=%s via OpenCV (%sx%s)", index, width, height)
                    return camera
                except Exception as exc:
                    errors.append(f"OpenCV /dev/video{index}: {exc}")
        logger.warning("camera attempt %s/%s failed: %s", attempt, retries, "; ".join(errors))
        time.sleep(1)

    raise RuntimeError(
        f"failed to open camera after {retries} attempts; "
        f"camera.backend={backend}, camera.index={index_config!r}; "
        "check the camera connection and run `libcamera-hello --list-cameras` or `ls /dev/video*`"
    )
