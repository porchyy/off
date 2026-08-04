"""WebRTC sender for the Pi Camera's in-memory live frame buffer."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from fractions import Fraction
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def signaling_url(backend_url: str, color_space: str = "rgb") -> str:
    parsed = urlparse(backend_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/api/camera/webrtc", "", f"role=pi&colorSpace={color_space}", ""))


class PiWebRtcSender:
    """Owns a single browser peer and sends frames without disk persistence."""

    def __init__(self, frames: Any, backend_url: str, fps: float, color_space: str = "rgb") -> None:
        self.frames = frames
        self.url = signaling_url(backend_url, color_space)
        self.fps = max(1.0, fps)
        self.color_space = color_space
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="postureai-webrtc", daemon=True)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._peer: Any | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(lambda: None)
        self._thread.join(timeout=5)

    def _run(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            logger.error("WebRTC sender stopped: %s", exc)

    async def _serve(self) -> None:
        import websockets  # type: ignore

        self._loop = asyncio.get_running_loop()
        retry_seconds = 1
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.url, open_timeout=5, ping_interval=20) as socket:
                    retry_seconds = 1
                    logger.info("WebRTC signaling connected")
                    async for raw in socket:
                        message = json.loads(raw)
                        if message.get("type") == "offer":
                            await self._answer_offer(socket, message)
                        elif message.get("type") == "stop":
                            await self._close_peer()
            except Exception as exc:
                if not self._stop.is_set():
                    logger.warning("WebRTC signaling unavailable: %s; retrying", exc)
                    await asyncio.sleep(retry_seconds)
                    retry_seconds = min(retry_seconds * 2, 10)
        await self._close_peer()

    async def _answer_offer(self, socket: Any, message: dict[str, Any]) -> None:
        from aiortc import RTCSessionDescription  # type: ignore

        await self._close_peer()
        peer = self._make_peer()
        self._peer = peer
        await peer.setRemoteDescription(RTCSessionDescription(sdp=message["sdp"], type="offer"))
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        await _wait_for_ice_complete(peer)
        await socket.send(json.dumps({"type": "answer", "sdp": peer.localDescription.sdp}))

    def _make_peer(self) -> Any:
        from aiortc import RTCPeerConnection, RTCRtpSender, VideoStreamTrack  # type: ignore
        from av import VideoFrame  # type: ignore

        frames = self.frames
        fps = self.fps
        color_space = self.color_space

        class LatestFrameTrack(VideoStreamTrack):
            kind = "video"

            def __init__(self) -> None:
                super().__init__()
                self._last_at = 0.0

            async def recv(self) -> Any:
                image = None
                while image is None:
                    now = asyncio.get_running_loop().time()
                    delay = max(0.0, (1.0 / fps) - (now - self._last_at))
                    if delay:
                        await asyncio.sleep(delay)
                    self._last_at = asyncio.get_running_loop().time()
                    image, _ = frames.get()
                    if image is None:
                        await asyncio.sleep(0.05)
                # Frames from CameraProducer are RGB. Keep this fallback for
                # alternate BGR camera implementations.
                if color_space == "bgr":
                    image = image[:, :, ::-1].copy()
                output = VideoFrame.from_ndarray(image, format="rgb24")
                output.pts = int(self._last_at * 90_000)
                output.time_base = Fraction(1, 90_000)
                return output

        peer = RTCPeerConnection()
        sender = peer.addTrack(LatestFrameTrack())
        transceiver = next(item for item in peer.getTransceivers() if item.sender is sender)
        codecs = RTCRtpSender.getCapabilities("video").codecs
        # H.264 is generally more efficient on the Pi/browser pair; leave VP8
        # available as a negotiated fallback.
        transceiver.setCodecPreferences(
            [codec for codec in codecs if codec.mimeType.lower() == "video/h264"]
            + [codec for codec in codecs if codec.mimeType.lower() != "video/h264"]
        )
        return peer

    async def _close_peer(self) -> None:
        if self._peer is not None:
            await self._peer.close()
            self._peer = None


async def _wait_for_ice_complete(peer: Any) -> None:
    if peer.iceGatheringState == "complete":
        return
    complete = asyncio.Event()

    @peer.on("icegatheringstatechange")
    def _changed() -> None:
        if peer.iceGatheringState == "complete":
            complete.set()

    await asyncio.wait_for(complete.wait(), timeout=5)
