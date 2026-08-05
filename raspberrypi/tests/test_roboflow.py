from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.roboflow import RoboflowPostureClient


def test_select_prediction_uses_the_highest_confident_posture(monkeypatch):
    monkeypatch.setenv("ROBOFLOW_API_KEY", "test-key")
    client = RoboflowPostureClient({"enabled": True, "confidence": 0.6})

    result = client._select_prediction({
        "predictions": [
            {"class": "good_posture", "confidence": 0.72},
            {"class": "slouch", "confidence": 0.91},
            {"class": "leaning_forward", "confidence": 0.4},
        ]
    })

    assert result == {
        "label": "slouch",
        "confidence": 0.91,
        "model": "sitting-posture-detection-3933f/2",
    }


def test_disabled_client_never_attempts_an_inference():
    client = RoboflowPostureClient({"enabled": False})

    assert client.infer_if_due("not-an-image") is None
