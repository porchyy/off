"""HTTP uploader + offline buffer."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


class Uploader:
    """Send samples/alerts to backend. Falls back to a local SQLite buffer on error."""

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        buffer_path: str | Path = "buffer.sqlite",
        sample_interval_seconds: float = 60.0,
    ) -> None:
        self._base = url.rstrip("/")
        self._timeout = timeout
        self._lock = threading.Lock()
        self._buffer_path = Path(buffer_path)
        self._sample_interval_seconds = max(1.0, sample_interval_seconds)
        self._sample_started_at: float | None = None
        self._sample_total: dict[str, float] = {}
        self._sample_count = 0
        self._init_buffer()

    def _init_buffer(self) -> None:
        with sqlite3.connect(self._buffer_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            conn.commit()

    def send_sample(self, sample: dict[str, Any]) -> bool:
        """Average high-rate detector output before storing it in the backend."""
        with self._lock:
            now = time.monotonic()
            if self._sample_started_at is None:
                self._sample_started_at = now
            self._sample_count += 1
            for key, value in sample.items():
                self._sample_total[key] = self._sample_total.get(key, 0.0) + float(value)
            if now - self._sample_started_at < self._sample_interval_seconds:
                return True
            payload = self._take_sample_locked()
        return self._post("/api/samples", payload) if payload else True

    def flush_sample(self) -> bool:
        """Persist a final partial interval before the Pi client shuts down."""
        with self._lock:
            payload = self._take_sample_locked()
        return self._post("/api/samples", payload) if payload else True

    def _take_sample_locked(self) -> dict[str, Any] | None:
        if not self._sample_count:
            return None
        payload = {key: value / self._sample_count for key, value in self._sample_total.items()}
        self._sample_started_at = None
        self._sample_total = {}
        self._sample_count = 0
        return payload

    def send_alert(self, alert: dict[str, Any]) -> bool:
        return self._post("/api/alerts", alert)

    def send_frame(self, jpeg: bytes) -> bool:
        """Upload only the newest preview frame; never buffer camera images."""
        try:
            response = requests.put(
                f"{self._base}/api/camera/frame",
                data=jpeg,
                headers={"content-type": "image/jpeg"},
                timeout=self._timeout,
            )
            if response.ok:
                return True
            logger.warning("backend returned %s for camera frame", response.status_code)
        except requests.RequestException as exc:
            logger.warning("could not upload camera frame: %s", exc)
        return False

    def fetch_settings(self) -> dict[str, Any] | None:
        """Read dashboard settings without buffering when the backend is offline."""
        try:
            response = requests.get(f"{self._base}/api/settings", timeout=self._timeout)
            if response.ok:
                payload = response.json()
                return payload if isinstance(payload, dict) else None
            logger.warning("backend returned %s for settings sync", response.status_code)
        except requests.RequestException as exc:
            logger.warning("could not sync settings from backend: %s", exc)
        return None

    def send_client_status(self, *, online: bool, last_sync_at: str | None, message: str | None = None) -> bool:
        try:
            response = requests.put(
                f"{self._base}/api/client/status",
                json={"online": online, "lastSyncAt": last_sync_at, "message": message},
                timeout=self._timeout,
            )
            return response.ok
        except requests.RequestException as exc:
            logger.debug("could not publish Pi client status: %s", exc)
            return False

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
