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
    with pytest.raises(ValueError, match="only yolov5"):
        validate_config({"detection": {"mode": "remote"}}, tmp_path / "config.yaml")


def test_config_migrates_existing_mediapipe_settings_to_yolov5(tmp_path):
    config = validate_config(
        {"detection": {"mode": "mediapipe", "model": "../frontend/public/models/pose_landmarker_full.task"}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["mode"] == "yolov5"
    assert Path(config["detection"]["model"]).name == "small640.pt"


def test_config_validates_led_pin_as_bcm_gpio(tmp_path):
    config = validate_config({"indicator": {"enabled": True, "pin": 17}}, tmp_path / "config.yaml")

    assert config["indicator"] == {"enabled": True, "pin": 17, "active_high": True, "threshold": 50.0}

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
    assert config["detection"]["interval"] == 0.5
    assert config["detection"]["enabled"] is True
    assert config["detection"]["mode"] == "yolov5"
    assert config["detection"]["confidence"] == 0.5
    assert config["detection"]["iou"] == 0.5
    assert Path(config["detection"]["model"]).name == "small640.pt"
    assert Path(config["detection"]["model"]).parent.name == "models"
    assert config["roboflow"] == {
        "enabled": False,
        "model_id": "sitting-posture-detection-3933f/2",
        "interval": 1.0,
        "confidence": 0.6,
        "timeout": 8.0,
        "input_width": 640,
        "api_key_env": "ROBOFLOW_API_KEY",
    }


def test_config_clamps_yolov5_confidence_options(tmp_path):
    config = validate_config(
        {"detection": {"confidence": 4, "iou": -3}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["confidence"] == 1.0
    assert config["detection"]["iou"] == 0.05


def test_config_can_disable_yolov5_without_disabling_roboflow(tmp_path):
    config = validate_config(
        {"detection": {"enabled": False}, "roboflow": {"enabled": True}},
        tmp_path / "config.yaml",
    )

    assert config["detection"]["enabled"] is False
    assert config["roboflow"]["enabled"] is True
