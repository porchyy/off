"""In-memory latest frame from the Raspberry Pi camera.

Frames are deliberately not written to disk.  The store only keeps the most
recent JPEG so a dashboard on the local network can display the Pi camera.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


class CameraFrameStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jpeg: bytes | None = None
        self._updated_at: str | None = None

    def put(self, jpeg: bytes) -> None:
        with self._lock:
            self._jpeg = jpeg
            self._updated_at = datetime.now(timezone.utc).isoformat()

    def get(self) -> tuple[bytes | None, str | None]:
        with self._lock:
            return self._jpeg, self._updated_at


camera_frames = CameraFrameStore()
