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
