from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.lcd import CharacterLcd


def test_lcd_1602_lines_fit_the_display_and_show_posture_state():
    lines = CharacterLcd.format_metrics({"score": 82}, columns=16, risk_threshold=60)

    assert lines == (" SCORE:  82/100 ", "  GOOD POSTURE  ")
    assert all(len(line) == 16 for line in lines)


def test_lcd_1602_uses_risk_message_for_low_score():
    _, line = CharacterLcd.format_metrics({"score": 39}, columns=16, risk_threshold=60)

    assert line == " ADJUST POSTURE "


def test_lcd_1602_marks_scores_from_60_to_79_as_check_posture():
    _, line = CharacterLcd.format_metrics({"score": 69}, columns=16, risk_threshold=60)

    assert line == " CHECK POSTURE  "


def test_lcd_1602_shows_the_trained_classifier_label_when_it_was_used():
    _, line = CharacterLcd.format_metrics(
        {"score": 30, "posture_label": "slouch", "posture_ai_used": True},
        columns=16,
        risk_threshold=60,
    )

    assert line == " SLOUCH DETECT  "


def test_lcd_1602_prompts_for_a_complete_pose_and_clears_stale_scores():
    lcd = object.__new__(CharacterLcd)
    lcd.cols = 16
    lines = []
    lcd._write = lambda value: lines.append(value) or True

    assert lcd.show_incomplete_pose() is True
    assert lcd.show_waiting_for_pose() is True
    assert lines == [
        (" POSE NOT READY ", "PLEASE SIT WELL "),
        ("POSTUREAI READY ", "WAITING FOR POSE"),
    ]
