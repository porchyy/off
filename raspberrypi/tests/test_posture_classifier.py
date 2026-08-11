from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.posture_classifier import CLASS_LABELS, score_for_label


def test_kanden_class_order_matches_the_published_model_card():
    assert CLASS_LABELS == ("good", "slouch", "chin_rest", "stretch")


def test_kanden_labels_map_to_safe_dashboard_scores():
    assert score_for_label("good") == 100.0
    assert score_for_label("stretch") == 80.0
    assert score_for_label("slouch") < 60.0
    assert score_for_label("chin_rest") < score_for_label("slouch")
