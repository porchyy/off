from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.indicator import GpioLed


def test_blink_flashes_twice_and_leaves_the_led_off(monkeypatch):
    indicator = object.__new__(GpioLed)
    events: list[str] = []
    indicator.on = lambda: events.append("on") or True
    indicator.off = lambda: events.append("off") or True
    monkeypatch.setattr("client.indicator.time.sleep", lambda _: None)

    assert indicator.blink(times=2, on_seconds=0.1, off_seconds=0.1) is True
    assert events == ["on", "off", "on", "off"]
