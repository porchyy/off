from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.alert import AlertController


class FakeUploader:
    def __init__(self) -> None:
        self.alerts = []

    def send_alert(self, alert):
        self.alerts.append(alert)
        return True


class FakeSound:
    def __init__(self) -> None:
        self.play_count = 0

    def play(self):
        self.play_count += 1
        return True


class FakeIndicator:
    def __init__(self) -> None:
        self.on_count = 0
        self.off_count = 0

    def on(self):
        self.on_count += 1

    def off(self):
        self.off_count += 1


def test_alert_waits_for_risk_duration_and_respects_cooldown():
    now = [100.0]
    uploader = FakeUploader()
    sound = FakeSound()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 10, "cooldown": 30}},
        uploader,
        sound,
        clock=lambda: now[0],
    )

    assert controller.update({"score": 50}) is False
    now[0] = 109.9
    assert controller.update({"score": 40}) is False
    now[0] = 110.0
    assert controller.update({"score": 40}) is True
    assert sound.play_count == 1
    assert len(uploader.alerts) == 1

    now[0] = 120.0
    assert controller.update({"score": 35}) is False
    now[0] = 140.0
    assert controller.update({"score": 35}) is True
    assert sound.play_count == 2


def test_good_posture_resets_low_score_timer():
    now = [0.0]
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 5}},
        FakeUploader(),
        FakeSound(),
        clock=lambda: now[0],
    )

    assert controller.update({"score": 50}) is False
    now[0] = 4.0
    assert controller.update({"score": 80}) is False
    now[0] = 6.0
    assert controller.update({"score": 50}) is False
    now[0] = 11.0
    assert controller.update({"score": 50}) is True


def test_led_turns_on_for_persistent_risk_and_off_when_posture_recovers():
    now = [0.0]
    indicator = FakeIndicator()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 5}},
        FakeUploader(),
        FakeSound(),
        indicator,
        clock=lambda: now[0],
    )

    controller.update({"score": 50})
    assert indicator.on_count == 0
    now[0] = 5.0
    assert controller.update({"score": 50}) is True
    assert indicator.on_count == 1
    controller.update({"score": 75})
    assert indicator.off_count == 1


def test_dashboard_settings_apply_without_restarting_client():
    sound = FakeSound()
    sound.enabled = True
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 45}},
        FakeUploader(),
        sound,
    )

    assert controller.apply_runtime_settings({"riskThreshold": 72, "riskSeconds": 20, "soundEnabled": False}) is True
    assert controller.threshold == 72
    assert controller.risk_seconds == 20
    assert sound.enabled is False
