"""HTTP uploader + offline buffer."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


class Uploader:
    """Send samples/alerts to backend. Falls back to a local SQLite buffer on error."""

    def __init__(self, url: str, timeout: float = 5.0, buffer_path: str | Path = "buffer.sqlite") -> None:
        self._base = url.rstrip("/")
        self._timeout = timeout
        self._lock = threading.Lock()
        self._buffer_path = Path(buffer_path)
        self._init_buffer()

    def _init_buffer(self) -> None:
        with sqlite3.connect(self._buffer_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            conn.commit()

    def send_sample(self, sample: dict[str, Any]) -> bool:
        return self._post("/api/samples", sample)

    def send_alert(self, alert: dict[str, Any]) -> bool:
        return self._post("/api/alerts", alert)

    def _post(self, path: str, payload: dict[str, Any]) -> bool:
        try:
            response = requests.post(f"{self._base}{path}", json=payload, timeout=self._timeout)
            if response.ok:
                self._flush_buffer()
                return True
            logger.warning("backend returned %s for %s", response.status_code, path)
        except requests.RequestException as exc:
            logger.warning("backend unreachable (%s), buffering payload", exc)
        self._buffer(path, payload)
        return False

    def _buffer(self, path: str, payload: dict[str, Any]) -> None:
        kind = path.strip("/").split("/")[-1]
        with self._lock, sqlite3.connect(self._buffer_path) as conn:
            conn.execute(
                "INSERT INTO pending (kind, payload, created_at) VALUES (?, ?, ?)",
                (kind, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def _flush_buffer(self) -> None:
        with self._lock, sqlite3.connect(self._buffer_path) as conn:
            rows = conn.execute("SELECT id, kind, payload FROM pending ORDER BY id").fetchall()
            for row_id, kind, raw in rows:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    conn.execute("DELETE FROM pending WHERE id = ?", (row_id,))
                    continue
                response = requests.post(f"{self._base}/api/{kind}", json=payload, timeout=self._timeout)
                if not response.ok:
                    logger.info("still failing to flush buffered %s, will retry later", kind)
                    return
                conn.execute("DELETE FROM pending WHERE id = ?", (row_id,))
            conn.commit()
