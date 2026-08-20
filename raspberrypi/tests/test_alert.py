from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.alert import AlertController, SoundPlayer


class FakeUploader:
    def __init__(self) -> None:
        self.alerts = []

    def send_alert(self, alert):
        self.alerts.append(alert)
        return True


class FakeSound:
    def __init__(self) -> None:
        self.enabled = True
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


def test_sound_player_defaults_to_max98357a_only():
    player = SoundPlayer({})

    assert player.device == "plughw:CARD=MAX98357A,DEV=0"


def test_alert_waits_for_risk_duration_and_respects_cooldown():
    now = [100.0]
    uploader = FakeUploader()
    sound = FakeSound()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 10, "cooldown": 30}}, uploader, sound, clock=lambda: now[0]
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


def test_zero_risk_duration_alerts_immediately_and_respects_cooldown():
    now = [100.0]
    uploader = FakeUploader()
    sound = FakeSound()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 0, "cooldown": 30}}, uploader, sound, clock=lambda: now[0]
    )

    assert controller.update({"score": 50}) is True
    assert sound.play_count == 1
    assert len(uploader.alerts) == 1

    now[0] = 101.0
    assert controller.update({"score": 40}) is False
    assert sound.play_count == 1


def test_good_posture_resets_low_score_timer():
    now = [0.0]
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 5}}, FakeUploader(), FakeSound(), clock=lambda: now[0]
    )

    assert controller.update({"score": 50}) is False
    now[0] = 4.0
    assert controller.update({"score": 80}) is False
    now[0] = 6.0
    assert controller.update({"score": 50}) is False
    now[0] = 11.0
    assert controller.update({"score": 50}) is True


def test_led_turns_on_immediately_below_50_and_off_at_50():
    now = [0.0]
    indicator = FakeIndicator()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 5}, "indicator": {"threshold": 65, "delay_seconds": 5}},
        FakeUploader(),
        FakeSound(),
        indicator,
        clock=lambda: now[0],
    )

    assert controller.update({"score": 49}) is False
    assert indicator.on_count == 1
    controller.update({"score": 50})
    assert indicator.off_count == 1


def test_led_stays_on_while_the_score_remains_below_50():
    now = [0.0]
    indicator = FakeIndicator()
    controller = AlertController(
        {"indicator": {"threshold": 65, "delay_seconds": 5, "blink_seconds": 0.5}},
        FakeUploader(),
        FakeSound(),
        indicator,
        clock=lambda: now[0],
    )

    controller.update({"score": 49})
    assert indicator.on_count == 1
    now[0] = 0.49
    controller.update({"score": 49})
    assert indicator.off_count == 0
    now[0] = 0.5
    controller.update({"score": 49})
    assert indicator.on_count == 1
    controller.update({"score": 50})
    assert indicator.off_count == 1


def test_no_measurable_pose_turns_off_the_led_and_resets_the_risk_timer():
    indicator = FakeIndicator()
    controller = AlertController(
        {"risk": {"threshold": 60, "seconds": 5}, "indicator": {"threshold": 50, "delay_seconds": 5}},
        FakeUploader(),
        FakeSound(),
        indicator,
    )

    controller.update({"score": 49})
    controller.clear_posture()

    assert indicator.off_count == 1
    assert controller._indicator_is_on is False
    assert controller.low_since is None
    assert controller.indicator_low_since is None


def test_led_retries_turning_off_after_a_transient_gpio_failure():
    class FailingOffIndicator(FakeIndicator):
        def __init__(self) -> None:
            super().__init__()
            self.fail_first_off = True

        def on(self):
            self.on_count += 1
            return True

        def off(self):
            self.off_count += 1
            if self.fail_first_off:
                self.fail_first_off = False
                return False
            return True

    now = [0.0]
    indicator = FailingOffIndicator()
    controller = AlertController(
        {"indicator": {"threshold": 50, "delay_seconds": 0}},
        FakeUploader(),
        FakeSound(),
        indicator,
        clock=lambda: now[0],
    )

    controller.update({"score": 49})
    controller.update({"score": 50})
    assert controller._indicator_is_on is True
    controller.update({"score": 50})

    assert indicator.off_count == 2
    assert controller._indicator_is_on is False


def test_dashboard_settings_apply_without_restarting_client():
    sound = FakeSound()
    sound.enabled = True
    controller = AlertController({"risk": {"threshold": 60, "seconds": 45}}, FakeUploader(), sound)

    assert controller.apply_runtime_settings({"riskThreshold": 72, "riskSeconds": 20, "soundEnabled": False}) is True
    assert controller.threshold == 72
    assert controller.risk_seconds == 20
    assert sound.enabled is False

    assert controller.apply_runtime_settings({"riskSeconds": 0, "soundEnabled": True}) is True
    assert controller.risk_seconds == 0
    assert sound.enabled is True
