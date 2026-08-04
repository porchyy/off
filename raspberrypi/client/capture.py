"""Camera capture helpers."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LatestFrameBuffer:
    """Thread-safe in-memory handoff from the camera to AI and WebRTC."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: Any | None = None
        self._updated_at = 0.0

    def put(self, frame: Any) -> None:
        with self._lock:
            self._frame = frame
            self._updated_at = time.monotonic()

    def get(self) -> tuple[Any | None, float]:
        with self._lock:
            return self._frame, self._updated_at


class CameraProducer:
    """Continuously capture one Pi Camera stream for every local consumer."""

    def __init__(self, camera: "Camera", fps: float) -> None:
        self.camera = camera
        self.fps = max(1.0, fps)
        # Publish one normalized RGB frame to all consumers so AI and WebRTC
        # cannot disagree about channel order.
        self.color_space = "rgb" if camera.color_space == "bgr" else camera.color_space
        self.frames = LatestFrameBuffer()
        self.failures = 0
        self.last_error: Exception | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="postureai-camera", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def _run(self) -> None:
        interval = 1.0 / self.fps
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                ok, frame = self.camera.read()
                if not ok or frame is None:
                    raise RuntimeError("camera returned no frame")
                if self.camera.flip:
                    import cv2  # type: ignore
                    frame = cv2.flip(frame, self.camera.flip)
                if self.camera.color_space == "bgr":
                    import cv2  # type: ignore
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frames.put(frame)
                self.failures = 0
                self.last_error = None
            except Exception as exc:
                self.failures += 1
                self.last_error = exc
                logger.warning("live camera capture failed (%s): %s", self.failures, exc)
            remaining = interval - (time.monotonic() - started)
            if remaining > 0:
                self._stop.wait(remaining)


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
        # Request RGB directly from the Pi ISP so the shared live frame can
        # be sent to AI and WebRTC without channel-order conversion.
        main={"size": (width, height), "format": "RGB888"}
    ))
    camera.start()
    time.sleep(1.0)  # Allow auto-exposure to settle.
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
