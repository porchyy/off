from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import detect


def test_overlay_uses_anatomical_head_to_shoulder_connections():
    assert (7, 11) in detect.OVERLAY_CONNECTIONS
    assert (8, 12) in detect.OVERLAY_CONNECTIONS
    assert (0, 11) not in detect.OVERLAY_CONNECTIONS
    assert (0, 12) not in detect.OVERLAY_CONNECTIONS


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


def test_live_detection_forwards_compact_landmarks_to_overlay(monkeypatch):
    class FakeDetector:
        def calculate_metrics(self, frame, color_space):
            return {
                "score": 90.0,
                "neck": 1.0,
                "shoulders": 2.0,
                "torso": 3.0,
                "landmarks": [{"index": 11, "x": 0.4, "y": 0.5, "visibility": 0.9}],
            }

    class FakeUploader:
        def send_sample(self, metrics):
            self.metrics = metrics

    monkeypatch.setattr(detect, "get_detector", lambda: FakeDetector())
    monkeypatch.setattr(detect, "_last_analysis_at", 0.0)
    sent = []
    uploader = FakeUploader()

    detect.process_live_frame(
        "picamera-frame", {}, uploader, pose_callback=lambda metrics, landmarks: sent.append((metrics, landmarks))
    )

    assert uploader.metrics == {"score": 90.0, "neck": 1.0, "shoulders": 2.0, "torso": 3.0}
    assert sent == [(uploader.metrics, [{"index": 11, "x": 0.4, "y": 0.5, "visibility": 0.9}])]


def test_live_detection_shows_overlay_before_a_full_torso_score(monkeypatch):
    class FakeDetector:
        def calculate_metrics(self, frame, color_space):
            return {"landmarks": [{"index": 11, "x": 0.4, "y": 0.5, "visibility": 0.9}]}

    class FakeUploader:
        def send_sample(self, metrics):
            raise AssertionError("a partial pose must not be saved as a score")

    monkeypatch.setattr(detect, "get_detector", lambda: FakeDetector())
    monkeypatch.setattr(detect, "_last_analysis_at", 0.0)
    sent = []

    detect.process_live_frame(
        "picamera-frame", {}, FakeUploader(), pose_callback=lambda metrics, landmarks: sent.append((metrics, landmarks))
    )

    assert sent == [({}, [{"index": 11, "x": 0.4, "y": 0.5, "visibility": 0.9}])]


def test_overlay_ignores_non_image_test_frames():
    detect.draw_pose_overlay("not-an-image", [{"index": 11, "x": 0.4, "y": 0.5, "visibility": 0.9}])


def test_overlay_smoother_interpolates_landmarks_and_preserves_raw_score_path():
    smoother = detect.PoseOverlaySmoother()
    settings = {"alpha": 0.65, "hold_seconds": 0.2, "min_visibility": 0.35}

    first = smoother.update([{"index": 11, "x": 0.2, "y": 0.4, "visibility": 0.9}], 1.0, **settings)
    second = smoother.update([{"index": 11, "x": 0.6, "y": 0.8, "visibility": 0.9}], 1.1, **settings)

    assert first[0]["x"] == 0.2
    assert first[0]["y"] == 0.4
    assert second[0]["x"] == 0.46
    assert second[0]["y"] == 0.66


def test_overlay_smoother_holds_then_discards_missing_landmarks():
    smoother = detect.PoseOverlaySmoother()
    settings = {"alpha": 0.65, "hold_seconds": 0.2, "min_visibility": 0.35}

    smoother.update([{"index": 11, "x": 0.2, "y": 0.4, "visibility": 0.9}], 1.0, **settings)

    assert smoother.update([], 1.1, **settings)[0]["index"] == 11
    assert smoother.update([], 1.31, **settings) == []


def test_overlay_smoother_ignores_low_confidence_landmarks():
    smoother = detect.PoseOverlaySmoother()
    settings = {"alpha": 0.65, "hold_seconds": 0.2, "min_visibility": 0.35}

    assert smoother.update([{"index": 11, "x": 0.2, "y": 0.4, "visibility": 0.2}], 1.0, **settings) == []


def test_metric_smoother_rejects_a_single_score_spike():
    smoother = detect.PoseMetricSmoother()

    assert smoother.update({"score": 90, "neck": 10, "shoulders": 5, "torso": 8}, 0.35)["score"] == 90.0
    # A one-frame bad reading is removed by the median-of-three window.
    assert smoother.update({"score": 20, "neck": 50, "shoulders": 30, "torso": 40}, 0.35)["score"] == 90.0
    assert smoother.update({"score": 92, "neck": 9, "shoulders": 5, "torso": 8}, 0.35)["score"] == 90.0
    assert smoother.update({"score": 92, "neck": 9, "shoulders": 5, "torso": 8}, 0.35)["score"] == 90.7


def test_metric_smoother_resets_between_people_or_lost_poses():
    smoother = detect.PoseMetricSmoother()
    smoother.update({"score": 90, "neck": 10, "shoulders": 5, "torso": 8}, 0.35)
    smoother.reset()

    assert smoother.update({"score": 40, "neck": 35, "shoulders": 20, "torso": 30}, 0.35)["score"] == 40.0


def test_baseline_calibration_scores_deviation_instead_of_camera_offset():
    calibrator = detect.PostureBaselineCalibrator()
    calibrator.start(2, now=0)
    good = {"score": 10, "neck": 27, "shoulders": 24, "torso": 22}

    _, state = calibrator.apply(good, now=0.5)
    assert state["state"] == "collecting"
    calibrated, state = calibrator.apply(good, now=2.0)
    assert state["state"] == "ready"
    assert calibrated["score"] == 100.0

    worse, _ = calibrator.apply({"score": 0, "neck": 45, "shoulders": 24, "torso": 22}, now=2.1)
    assert worse["score"] < 100.0


def test_detector_initialization_fails_loudly_instead_of_using_fake_metrics(monkeypatch):
    class BrokenDetector:
        def __init__(self):
            raise ImportError("mediapipe unavailable")

    monkeypatch.setattr(detect, "MediaPipePoseDetector", BrokenDetector)
    monkeypatch.setattr(detect, "_pose_detector", None)

    with pytest.raises(RuntimeError, match="could not initialize MediaPipe Pose"):
        detect.get_detector("/tmp/pose_landmarker_full.task")
