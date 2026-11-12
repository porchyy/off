"""In-memory, LAN-only WebRTC signaling broker for one Pi camera viewer."""

from __future__ import annotations

import asyncio
from fastapi import WebSocket


class CameraSignalingBroker:
    """Relay SDP messages between one Pi client and one dashboard viewer."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pi: WebSocket | None = None
        self._viewer: WebSocket | None = None

    async def register(self, role: str, websocket: WebSocket, replace: bool = False) -> bool:
        async with self._lock:
            if role == "pi":
                if self._pi is not None and not replace:
                    return False
                if self._pi is not None and self._pi is not websocket:
                    try:
                        close_coro = getattr(self._pi, "close", None)
                        if callable(close_coro):
                            await close_coro(code=1000, reason="superseded by reconnecting pi")
                    except Exception:
                        pass
                self._pi = websocket
                return True
            if role == "viewer":
                if self._pi is None:
                    return False
                if self._viewer is not None and not replace:
                    return False
                if self._viewer is not None and self._viewer is not websocket:
                    try:
                        close_coro = getattr(self._viewer, "close", None)
                        if callable(close_coro):
                            await close_coro(code=1000, reason="superseded by reconnecting viewer")
                    except Exception:
                        pass
                self._viewer = websocket
                return True
        return False

    async def unregister(self, role: str, websocket: WebSocket) -> None:
        async with self._lock:
            if role == "pi" and self._pi is websocket:
                self._pi = None
            elif role == "viewer" and self._viewer is websocket:
                self._viewer = None

    async def peer(self, role: str) -> WebSocket | None:
        async with self._lock:
            return self._viewer if role == "pi" else self._pi

    async def status(self) -> dict[str, bool]:
        async with self._lock:
            return {"clientConnected": self._pi is not None, "viewerConnected": self._viewer is not None}


camera_signaling = CameraSignalingBroker()
