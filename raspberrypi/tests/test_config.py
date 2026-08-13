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

    assert config["indicator"] == {"enabled": True, "pin": 17, "active_high": True, "threshold": 50.0, "delay_seconds": 5.0}

    with pytest.raises(ValueError, match="indicator.pin"):
        validate_config({"indicator": {"pin": 40}}, tmp_path / "config.yaml")


def test_config_accepts_a_non_negative_led_gpiochip(tmp_path):
    config = validate_config({"indicator": {"chip": 15}}, tmp_path / "config.yaml")

    assert config["indicator"]["chip"] == 15

    with pytest.raises(ValueError, match="indicator.chip"):
        validate_config({"indicator": {"chip": -1}}, tmp_path / "config.yaml")


def test_config_supports_lcd_1602_i2c_defaults(tmp_path):
    config = validate_config({"lcd": {"enabled": True, "i2c_address": "0x3f"}}, tmp_path / "config.yaml")

    assert config["lcd"]["enabled"] is True
    assert config["lcd"]["i2c_address"] == 0x3F
    assert config["lcd"]["columns"] == 16
    assert config["lcd"]["rows"] == 2


def test_config_uses_live_video_defaults_and_ai_rate(tmp_path):
    config = validate_config({}, tmp_path / "config.yaml")

    assert config["video"] == {"enabled": True, "width": 640, "height": 360, "fps": 12.0}
    assert config["detection"]["interval"] == 0.1
    assert config["detection"]["enabled"] is True
    assert config["detection"]["overlay_smoothing_alpha"] == 0.65
    assert config["detection"]["overlay_hold_seconds"] == 0.2
    assert config["detection"]["overlay_min_visibility"] == 0.35
    assert config["detection"]["metric_smoothing_alpha"] == 0.35
    assert config["detection"]["score_source"] == "upper_body"
    assert config["recording"]["sample_interval_seconds"] == 60.0
    assert config["posture_classifier"] == {
        "enabled": False,
        "model": str(tmp_path / "models/kanden_posture_classifier.onnx"),
        "interval": 0.5,
        "min_confidence": 0.65,
    }


def test_config_clamps_overlay_smoothing_options(tmp_path):
    config = validate_config(
        {"detection": {"overlay_smoothing_alpha": 4, "overlay_hold_seconds": -1, "overlay_min_visibility": -3}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["overlay_smoothing_alpha"] == 0.95
    assert config["detection"]["overlay_hold_seconds"] == 0.0
    assert config["detection"]["overlay_min_visibility"] == 0.0


def test_config_clamps_metric_smoothing_option(tmp_path):
    config = validate_config({"detection": {"metric_smoothing_alpha": -3}}, tmp_path / "config.yaml")

    assert config["detection"]["metric_smoothing_alpha"] == 0.05


def test_config_resolves_and_clamps_the_kanden_classifier_options(tmp_path):
    config = validate_config(
        {"posture_classifier": {"model": "models/custom.onnx", "interval": 20, "min_confidence": -1}},
        tmp_path / "config.yaml",
    )

    assert config["posture_classifier"] == {
        "enabled": False,
        "model": str(tmp_path / "models/custom.onnx"),
        "interval": 5.0,
        "min_confidence": 0.0,
    }


def test_config_accepts_only_supported_score_sources(tmp_path):
    assert validate_config({"detection": {"score_source": "image_classifier"}}, tmp_path / "config.yaml")["detection"]["score_source"] == "image_classifier"

    with pytest.raises(ValueError, match="score_source"):
        validate_config({"detection": {"score_source": "hips"}}, tmp_path / "config.yaml")


def test_config_can_disable_mediapipe(tmp_path):
    config = validate_config({"detection": {"enabled": False}}, tmp_path / "config.yaml")

    assert config["detection"]["enabled"] is False
