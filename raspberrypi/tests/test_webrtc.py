from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.capture import LatestFrameBuffer
from client.webrtc import signaling_url


def test_signaling_url_uses_websocket_scheme_and_keeps_backend_host():
    assert signaling_url("http://localhost:8000") == "ws://localhost:8000/api/camera/webrtc?role=pi"
    assert signaling_url("https://pi.local") == "wss://pi.local/api/camera/webrtc?role=pi"


def test_latest_frame_buffer_keeps_only_the_latest_frame():
    buffer = LatestFrameBuffer()
    buffer.put("older")
    buffer.put("newest")

    frame, updated_at = buffer.get()
    assert frame == "newest"
    assert updated_at > 0
