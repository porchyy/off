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

    assert config["indicator"] == {"enabled": True, "pin": 17, "active_high": True}

    with pytest.raises(ValueError, match="indicator.pin"):
        validate_config({"indicator": {"pin": 40}}, tmp_path / "config.yaml")


def test_config_uses_live_video_defaults_and_ai_rate(tmp_path):
    config = validate_config({}, tmp_path / "config.yaml")

    assert config["video"] == {"enabled": True, "width": 640, "height": 480, "fps": 10.0}
    assert config["detection"]["interval"] == 0.2
