from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import detect


def test_detection_preserves_picamera_rgb_before_detection(monkeypatch):
    received = []

    class FakeDetector:
        def calculate_metrics(self, frame, color_space):
            received.append((frame, color_space))
            return {"score": 90.0, "neck": 1.0, "shoulders": 2.0, "torso": 3.0}

    class FakeCamera:
        color_space = "rgb"
        flip = 0

        def read(self):
            return True, "picamera-frame"

    class FakeUploader:
        samples = []

        def send_sample(self, metrics):
            self.samples.append(metrics)

    monkeypatch.setitem(sys.modules, "cv2", object())
    monkeypatch.setattr(detect, "get_detector", lambda: FakeDetector())
    uploader = FakeUploader()

    detect.run_detection_cycle(FakeCamera(), {}, uploader)

    assert received == [("picamera-frame", "rgb")]
    assert uploader.samples[0]["score"] == 90.0


def test_detector_initialization_fails_loudly_instead_of_using_fake_metrics(monkeypatch):
    class BrokenDetector:
        def __init__(self):
            raise ImportError("mediapipe unavailable")

    monkeypatch.setattr(detect, "MediaPipePoseDetector", BrokenDetector)
    monkeypatch.setattr(detect, "_pose_detector", None)

    with pytest.raises(RuntimeError, match="could not initialize MediaPipe Pose"):
        detect.get_detector("/tmp/pose_landmarker_full.task")
