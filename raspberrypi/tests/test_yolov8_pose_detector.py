from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.yolov8_pose_detector import YoloV8PoseDetector


def front_view_keypoints(*, head_x: float = 50, shoulder_left_y: float = 40, shoulder_right_y: float = 40, hip_x: float = 50):
    points = [[0.0, 0.0, 0.0] for _ in range(17)]
    points[3] = [head_x - 5, 20, 0.9]
    points[4] = [head_x + 5, 20, 0.9]
    points[5] = [35, shoulder_left_y, 0.9]
    points[6] = [65, shoulder_right_y, 0.9]
    points[11] = [hip_x - 12, 80, 0.9]
    points[12] = [hip_x + 12, 80, 0.9]
    return points


def test_front_view_upright_pose_is_perfect():
    result = YoloV8PoseDetector._analyze_keypoints(
        front_view_keypoints(), [20, 10, 80, 100], 0.95, 100, 120
    )

    assert result is not None
    assert result["posture"] == "perfect"
    assert result["score"] == 100.0
    assert result["neck"] == 0.0
    assert result["shoulders"] == 0.0
    assert result["torso"] == 0.0


def test_front_view_head_and_torso_lean_reduce_score():
    result = YoloV8PoseDetector._analyze_keypoints(
        front_view_keypoints(head_x=72, shoulder_left_y=32, shoulder_right_y=48, hip_x=25),
        [10, 10, 90, 100], 0.9, 100, 120,
    )

    assert result is not None
    assert result["posture"] == "bad"
    assert result["score"] < 70


def test_front_view_requires_ears_shoulders_and_hips():
    keypoints = front_view_keypoints()
    keypoints[4][2] = 0.1

    assert YoloV8PoseDetector._analyze_keypoints(keypoints, [20, 10, 80, 100], 0.9, 100, 120) is None
