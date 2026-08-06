"""WebRTC sender for the Pi Camera's in-memory live frame buffer."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import logging
import threading
from fractions import Fraction
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def signaling_url(backend_url: str) -> str:
    parsed = urlparse(backend_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/api/camera/webrtc", "", "role=pi", ""))


class PiWebRtcSender:
    """Owns a single browser peer and sends frames without disk persistence."""

    def __init__(
        self,
        frames: Any,
        backend_url: str,
        fps: float,
        color_space: str = "rgb",
        camera_format: str = "unknown",
        on_calibration_start: Callable[[], None] | None = None,
    ) -> None:
        self.frames = frames
        self.url = signaling_url(backend_url)
        self.fps = max(1.0, fps)
        self.color_space = color_space
        self.camera_format = camera_format
        self.on_calibration_start = on_calibration_start
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="postureai-webrtc", daemon=True)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._peer: Any | None = None
        self._pose_lock = threading.Lock()
        self._latest_pose: dict[str, Any] | None = None
        self._pose_revision = 0
        self._latest_roboflow: dict[str, Any] | None = None
        self._roboflow_revision = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(lambda: None)
        self._thread.join(timeout=5)

    def publish_pose(self, metrics: dict[str, Any], landmarks: list[dict[str, Any]]) -> None:
        """Store the newest compact AI result for the dashboard overlay."""
        with self._pose_lock:
            self._pose_revision += 1
            self._latest_pose = {
                "type": "pose_update",
                "metrics": dict(metrics),
                "landmarks": list(landmarks),
            }

    def publish_roboflow_result(self, result: dict[str, Any]) -> None:
        """Store the newest hosted posture classification for the dashboard."""
        with self._pose_lock:
            self._roboflow_revision += 1
            self._latest_roboflow = {"type": "roboflow_update", "result": dict(result)}

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
                    viewer_ready = asyncio.Event()
                    send_lock = asyncio.Lock()
                    pose_task = asyncio.create_task(self._send_pose_updates(socket, viewer_ready, send_lock))
                    try:
                        async for raw in socket:
                            message = json.loads(raw)
                            if message.get("type") == "offer":
                                # CameraProducer publishes RGB camera frames to
                                # the sender, which builds the WebRTC frame as rgb24.
                                display_mode = "RGB3" if self.color_space == "rgb" else "BGR3"
                                async with send_lock:
                                    await socket.send(json.dumps({
                                        "type": "stream_info",
                                        "cameraFormat": self.camera_format,
                                        "displayColorMode": display_mode,
                                        "outputColorSpace": self.color_space,
                                    }))
                                await self._answer_offer(socket, message)
                                viewer_ready.set()
                            elif message.get("type") == "stop":
                                viewer_ready.clear()
                                await self._close_peer()
                            elif message.get("type") == "calibration_start":
                                if self.on_calibration_start is None:
                                    logger.warning("dashboard requested calibration while MediaPipe is disabled")
                                else:
                                    self.on_calibration_start()
                                    await socket.send(json.dumps({"type": "calibration_status", "state": "started"}))
                            elif message.get("type") == "error" and message.get("code") == "peer_unavailable":
                                viewer_ready.clear()
                    finally:
                        pose_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await pose_task
            except Exception as exc:
                if not self._stop.is_set():
                    logger.warning("WebRTC signaling unavailable: %s; retrying", exc)
                    await asyncio.sleep(retry_seconds)
                    retry_seconds = min(retry_seconds * 2, 10)
        await self._close_peer()

    async def _send_pose_updates(
        self, socket: Any, viewer_ready: asyncio.Event, send_lock: asyncio.Lock
    ) -> None:
        """Forward only the most recent landmarks, never a queue of stale poses."""
        delivered_revision = 0
        delivered_roboflow_revision = 0
        while not self._stop.is_set():
            await viewer_ready.wait()
            with self._pose_lock:
                revision = self._pose_revision
                payload = self._latest_pose
            if payload is not None and revision > delivered_revision:
                async with send_lock:
                    await socket.send(json.dumps(payload, separators=(",", ":")))
                delivered_revision = revision
            with self._pose_lock:
                roboflow_revision = self._roboflow_revision
                roboflow_payload = self._latest_roboflow
            if roboflow_payload is not None and roboflow_revision > delivered_roboflow_revision:
                async with send_lock:
                    await socket.send(json.dumps(roboflow_payload, separators=(",", ":")))
                delivered_roboflow_revision = roboflow_revision
            await asyncio.sleep(0.03)

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
