from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import detect


def test_live_detection_passes_camera_color_metadata_to_detector(monkeypatch):
    received = []

    class FakeDetector:
        def calculate_metrics(self, frame, color_space):
            received.append((frame, color_space))
            return {"score": 90.0, "neck": 1.0, "shoulders": 2.0, "torso": 3.0}

    class FakeUploader:
        samples = []

        def send_sample(self, metrics):
            self.samples.append(metrics)

    monkeypatch.setattr(detect, "get_detector", lambda: FakeDetector())
    uploader = FakeUploader()

    detect.process_live_frame("picamera-frame", {}, uploader, color_space="bgr")

    assert received == [("picamera-frame", "bgr")]
    assert uploader.samples[0]["score"] == 90.0


def test_detector_initialization_fails_loudly_instead_of_using_fake_metrics(monkeypatch):
    class BrokenDetector:
        def __init__(self):
            raise ImportError("mediapipe unavailable")

    monkeypatch.setattr(detect, "MediaPipePoseDetector", BrokenDetector)
    monkeypatch.setattr(detect, "_pose_detector", None)

    with pytest.raises(RuntimeError, match="could not initialize MediaPipe Pose"):
        detect.get_detector("/tmp/pose_landmarker_full.task")
