from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from posture_client import validate_config


def test_config_resolves_buffer_relative_to_config_file(tmp_path):
    config = validate_config({"buffer": {"path": "state/pending.sqlite"}}, tmp_path / "config.yaml")

    assert config["buffer"]["path"] == str(tmp_path / "state/pending.sqlite")
    assert config["backend"]["url"] == "http://localhost:8000"


def test_config_rejects_unimplemented_remote_detection_mode(tmp_path):
    with pytest.raises(ValueError, match="only mediapipe"):
        validate_config({"detection": {"mode": "remote"}}, tmp_path / "config.yaml")


def test_config_validates_led_pin_as_bcm_gpio(tmp_path):
    config = validate_config({"indicator": {"enabled": True, "pin": 17}}, tmp_path / "config.yaml")

    assert config["indicator"] == {"enabled": True, "pin": 17, "active_high": True, "threshold": 50.0}

    with pytest.raises(ValueError, match="indicator.pin"):
        validate_config({"indicator": {"pin": 40}}, tmp_path / "config.yaml")


def test_config_uses_live_video_defaults_and_ai_rate(tmp_path):
    config = validate_config({}, tmp_path / "config.yaml")

    assert config["video"] == {"enabled": True, "width": 640, "height": 360, "fps": 12.0}
    assert config["detection"]["interval"] == 0.1
    assert config["detection"]["enabled"] is True
    assert config["detection"]["overlay_smoothing_alpha"] == 0.65
    assert config["detection"]["overlay_hold_seconds"] == 0.2
    assert config["detection"]["overlay_min_visibility"] == 0.35
    assert config["roboflow"] == {
        "enabled": False,
        "model_id": "sitting-posture-detection-3933f/2",
        "interval": 1.0,
        "confidence": 0.6,
        "timeout": 8.0,
        "input_width": 640,
        "api_key_env": "ROBOFLOW_API_KEY",
    }


def test_config_clamps_overlay_smoothing_options(tmp_path):
    config = validate_config(
        {"detection": {"overlay_smoothing_alpha": 4, "overlay_hold_seconds": -1, "overlay_min_visibility": -3}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["overlay_smoothing_alpha"] == 0.95
    assert config["detection"]["overlay_hold_seconds"] == 0.0
    assert config["detection"]["overlay_min_visibility"] == 0.0


def test_config_can_disable_mediapipe_without_disabling_roboflow(tmp_path):
    config = validate_config(
        {"detection": {"enabled": False}, "roboflow": {"enabled": True}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["enabled"] is False
    assert config["roboflow"]["enabled"] is True
