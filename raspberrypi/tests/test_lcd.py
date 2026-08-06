from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.lcd import CharacterLcd


def test_lcd_1602_lines_fit_the_display_and_show_posture_state():
    lines = CharacterLcd.format_metrics({"score": 82}, columns=16, risk_threshold=60)

    assert lines == ("SCORE:  82/100  ", "GOOD POSTURE    ")
    assert all(len(line) == 16 for line in lines)


def test_lcd_1602_uses_risk_message_for_low_score():
    _, line = CharacterLcd.format_metrics({"score": 42}, columns=16, risk_threshold=60)

    assert line == "ADJUST POSTURE  "
