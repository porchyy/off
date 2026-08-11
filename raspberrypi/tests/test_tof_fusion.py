from __future__ import annotations

from datetime import datetime, timezone

from client.tof_fusion import Tof400cFusion


class Response:
    ok = True

    def __init__(self, distance: float) -> None:
        self.distance = distance
        self.closed = False

    def json(self):
        return {
            "distanceCm": self.distance,
            "vl53l1xOk": True,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

    def close(self) -> None:
        self.closed = True


def test_tof400c_auto_calibrates_then_only_lowers_the_camera_score() -> None:
    clock = {"now": 0.0}
    distances = iter([75.0, 75.0, 75.0, 63.0, 63.0, 63.0])

    def fetch(_url, *, timeout):
        assert timeout == 0.1
        return Response(next(distances))

    fusion = Tof400cFusion(
        "http://localhost:8000",
        {"poll_seconds": 0.1, "calibration_samples": 3, "forward_start_cm": 8, "forward_points_per_cm": 2},
        fetch=fetch,
        clock=lambda: clock["now"],
    )
    metrics = {"score": 100.0, "neck": 0.0, "shoulders": 0.0, "torso": 0.0}

    for _ in range(3):
        clock["now"] += 0.2
        calibrated = fusion.apply(metrics)

    assert calibrated["tof_baseline_cm"] == 75.0
    assert calibrated["score"] == 100.0

    for _ in range(3):
        clock["now"] += 0.2
        leaning = fusion.apply(metrics)

    assert leaning["tof_distance_cm"] == 63.0
    assert leaning["tof_delta_cm"] == 12.0
    assert leaning["tof_penalty"] == 8.0
    assert leaning["score"] == 92.0


def test_tof400c_never_raises_a_low_camera_score() -> None:
    def fetch(_url, *, timeout):
        return Response(75.0)

    fusion = Tof400cFusion(
        "http://localhost:8000",
        {"poll_seconds": 0.1, "calibration_samples": 3},
        fetch=fetch,
        clock=lambda: 1.0,
    )
    metrics = {"score": 70.0, "neck": 0.0, "shoulders": 0.0, "torso": 0.0}

    result = fusion.apply(metrics)

    assert result["score"] == 70.0
    assert result["tof_baseline_cm"] is None
