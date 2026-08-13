from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.uploader import Uploader


def test_uploader_averages_detector_samples_before_posting(tmp_path, monkeypatch):
    uploader = Uploader("http://backend", buffer_path=tmp_path / "buffer.sqlite", sample_interval_seconds=60)
    posted = []
    monkeypatch.setattr(uploader, "_post", lambda path, payload: posted.append((path, payload)) or True)

    assert uploader.send_sample({"score": 80, "neck": 4, "shoulders": 2, "torso": 1})
    assert uploader.send_sample({"score": 60, "neck": 8, "shoulders": 6, "torso": 3})
    assert posted == []

    assert uploader.flush_sample()
    assert posted == [
        ("/api/samples", {"score": 70.0, "neck": 6.0, "shoulders": 4.0, "torso": 2.0})
    ]
