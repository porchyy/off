"""CSV/JSON export helpers — mirror the original Node server's format."""

from __future__ import annotations

import csv
import io
from typing import Iterable

COLUMNS = [
    "type", "id", "score", "neck", "shoulders", "torso",
    "severity", "message", "created_at",
]


def rows_to_csv(rows: Iterable[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col) for col in COLUMNS})
    return buffer.getvalue()
