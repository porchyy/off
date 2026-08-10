"""Unit tests for backend export module."""

import pytest
from app.export import rows_to_csv, COLUMNS


def test_columns_list():
    assert "type" in COLUMNS
    assert "score" in COLUMNS
    assert "severity" in COLUMNS
    assert "created_at" in COLUMNS


def test_rows_to_csv_empty():
    result = rows_to_csv([])
    lines = result.splitlines()
    assert len(lines) == 1
    assert lines[0] == ",".join(COLUMNS)


def test_rows_to_csv_sample_and_alert():
    rows = [
        {
            "type": "sample",
            "id": 1,
            "score": 85.5,
            "neck": 10.0,
            "shoulders": 5.0,
            "torso": 2.0,
            "severity": None,
            "message": None,
            "created_at": "2026-07-26T00:00:00Z",
        },
        {
            "type": "alert",
            "id": 2,
            "score": None,
            "neck": None,
            "shoulders": None,
            "torso": None,
            "severity": "risk",
            "message": "Poor posture detected",
            "created_at": "2026-07-26T00:05:00Z",
        },
    ]
    result = rows_to_csv(rows)
    lines = result.splitlines()
    assert len(lines) == 3
    assert lines[0] == ",".join(COLUMNS)
    assert "sample,1,85.5" in lines[1]
    assert "alert,2" in lines[2]
    assert "Poor posture detected" in lines[2]
