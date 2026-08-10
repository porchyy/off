from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.yolov5_detector import YoloV5PostureDetector


def test_select_prediction_maps_upstream_good_class_to_full_score():
    result = YoloV5PostureDetector._select_prediction([
        {"class": 0, "confidence": 0.91, "xmin": 1, "ymin": 2, "xmax": 30, "ymax": 40},
    ])

    assert result is not None
    assert result["posture"] == "sitting_good"
    assert result["score"] == 100.0
    assert result["bbox"] == {"x1": 1, "y1": 2, "x2": 30, "y2": 40}


def test_select_prediction_maps_upstream_bad_class_to_zero_score():
    result = YoloV5PostureDetector._select_prediction([
        {"class": 0, "confidence": 0.55},
        {"class": 1, "confidence": 0.86, "xmin": 3, "ymin": 4, "xmax": 50, "ymax": 60},
    ])

    assert result is not None
    assert result["posture"] == "sitting_bad"
    assert result["score"] == 0.0


def test_select_prediction_ignores_unknown_classes():
    assert YoloV5PostureDetector._select_prediction([{"class": 3, "confidence": 0.9}]) is None
