from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.indicator import GpioLed
from client.indicator import _detect_lgpio_chip


def test_detect_lgpio_chip_finds_pi5_rp1_controller(tmp_path):
    chip = tmp_path / "gpiochip569"
    chip.mkdir()
    (chip / "label").write_text("pinctrl-rp1\n", encoding="utf-8")
    (chip / "dev").write_text("254:15\n", encoding="utf-8")

    assert _detect_lgpio_chip(tmp_path) == 15


def test_detect_lgpio_chip_falls_back_to_the_sysfs_index_without_a_dev_entry(tmp_path):
    chip = tmp_path / "gpiochip15"
    chip.mkdir()
    (chip / "label").write_text("pinctrl-rp1\n", encoding="utf-8")

    assert _detect_lgpio_chip(tmp_path) == 15


def test_direct_lgpio_fallback_controls_an_active_high_led():
    class FakeLgpio:
        def __init__(self):
            self.writes = []

        def gpio_write(self, handle, pin, level):
            self.writes.append((handle, pin, level))

    indicator = object.__new__(GpioLed)
    indicator._led = None
    indicator._lgpio = FakeLgpio()
    indicator._lgpio_handle = 99
    indicator.pin = 17
    indicator.active_high = True
    indicator._is_on = False

    assert indicator.on() is True
    assert indicator.off() is True
    assert indicator._lgpio.writes == [(99, 17, 1), (99, 17, 0)]


def test_blink_flashes_twice_and_leaves_the_led_off(monkeypatch):
    indicator = object.__new__(GpioLed)
    events: list[str] = []
    indicator.on = lambda: events.append("on") or True
    indicator.off = lambda: events.append("off") or True
    monkeypatch.setattr("client.indicator.time.sleep", lambda _: None)

    assert indicator.blink(times=2, on_seconds=0.1, off_seconds=0.1) is True
    assert events == ["on", "off", "on", "off"]
