"""Fuse TOF400C readings from the sensor service into posture metrics."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from statistics import median
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Tof400cFusion:
    """Use a fixed camera-mounted TOF400C as a front/back posture signal.

    The sensor publisher remains the only process that opens I2C.  This class
    reads its newest value from the local backend, so it cannot contend with
    ``postureai-sensors`` for the VL53L1X device.
    """

    def __init__(
        self,
        backend_url: str,
        settings: dict[str, Any],
        *,
        fetch: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.enabled = bool(settings.get("enabled", True))
        self.poll_seconds = min(5.0, max(0.1, float(settings.get("poll_seconds", 0.5))))
        self.stale_seconds = min(30.0, max(1.0, float(settings.get("stale_seconds", 3.0))))
        self.calibration_samples = min(30, max(3, int(settings.get("calibration_samples", 6))))
        self.absence_reset_seconds = min(60.0, max(2.0, float(settings.get("absence_reset_seconds", 8.0))))
        self.forward_start_cm = min(100.0, max(0.0, float(settings.get("forward_start_cm", 8.0))))
        self.recline_start_cm = min(100.0, max(0.0, float(settings.get("recline_start_cm", 10.0))))
        self.forward_points_per_cm = min(10.0, max(0.1, float(settings.get("forward_points_per_cm", 2.0))))
        self.recline_points_per_cm = min(10.0, max(0.1, float(settings.get("recline_points_per_cm", 1.5))))
        self.max_forward_penalty = min(60.0, max(0.0, float(settings.get("max_forward_penalty", 35.0))))
        self.max_recline_penalty = min(60.0, max(0.0, float(settings.get("max_recline_penalty", 25.0))))
        self._url = f"{backend_url.rstrip('/')}/api/sensors/latest"
        self._fetch = fetch
        self._clock = clock
        self._last_poll = -float("inf")
        self._distance_cm: float | None = None
        self._distance_samples: deque[float] = deque(maxlen=3)
        self._baseline_samples: deque[float] = deque(maxlen=self.calibration_samples)
        self._baseline_cm: float | None = None
        self._missing_since: float | None = None
        self._status = "รอ TOF400C"

    @staticmethod
    def _fresh(payload: dict[str, Any], stale_seconds: float) -> bool:
        value = payload.get("updatedAt")
        if not isinstance(value, str):
            return False
        try:
            updated = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - updated).total_seconds() <= stale_seconds

    def _refresh(self) -> None:
        now = self._clock()
        if now - self._last_poll < self.poll_seconds:
            return
        self._last_poll = now
        try:
            fetch = self._fetch
            if fetch is None:
                import requests  # type: ignore

                fetch = requests.get
            # The camera loop must remain responsive if the local backend is
            # restarting, so a sensor refresh never waits longer than 0.2 s.
            response = fetch(self._url, timeout=min(0.2, self.poll_seconds))
            try:
                if not getattr(response, "ok", False):
                    raise RuntimeError(f"sensor API returned {getattr(response, 'status_code', 'an error')}")
                payload = response.json()
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
            if not isinstance(payload, dict) or not payload.get("vl53l1xOk") or not self._fresh(payload, self.stale_seconds):
                self._distance_cm = None
                self._status = "TOF400C ไม่พร้อม"
                return
            distance = float(payload.get("distanceCm"))
            if distance < 0:
                raise ValueError("TOF400C returned a negative distance")
            self._distance_samples.append(distance)
            self._distance_cm = round(float(median(self._distance_samples)), 1)
        except Exception as error:
            self._distance_cm = None
            self._status = "TOF400C ไม่พร้อม"
            logger.debug("could not read TOF400C sensor service: %s", error)

    def _reset_baseline(self) -> None:
        self._baseline_samples.clear()
        self._baseline_cm = None
        self._status = "รอปรับเทียบ TOF400C"

    def pose_missing(self) -> None:
        if not self.enabled:
            return
        now = self._clock()
        if self._missing_since is None:
            self._missing_since = now
        elif now - self._missing_since >= self.absence_reset_seconds:
            self._reset_baseline()

    def apply(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Return metrics with a TOF penalty that can only lower the score."""
        result = dict(metrics)
        if not self.enabled:
            result["tof_status"] = "TOF400C ปิดอยู่"
            return result
        self._missing_since = None
        self._refresh()
        if self._distance_cm is None:
            result.update({"tof_status": self._status, "tof_distance_cm": None, "tof_baseline_cm": self._baseline_cm, "tof_delta_cm": None, "tof_penalty": 0.0})
            return result

        distance = self._distance_cm
        result["tof_distance_cm"] = distance
        if self._baseline_cm is None:
            eligible = (
                float(result.get("score", 0)) >= 80.0
                and float(result.get("neck", 99)) <= 6.0
                and float(result.get("shoulders", 99)) <= 10.0
                and abs(float(result.get("torso", 99))) <= 5.0
            )
            if eligible:
                self._baseline_samples.append(distance)
            if len(self._baseline_samples) == self.calibration_samples:
                self._baseline_cm = round(float(median(self._baseline_samples)), 1)
                self._status = "TOF400C พร้อมใช้งาน"
            else:
                self._status = f"กำลังปรับเทียบ TOF400C ({len(self._baseline_samples)}/{self.calibration_samples})"
            result.update({"tof_status": self._status, "tof_baseline_cm": self._baseline_cm, "tof_delta_cm": None, "tof_penalty": 0.0})
            return result

        # Sensor and camera are fixed together and point at the upper torso.
        # Moving closer makes distance smaller, so a positive delta is a
        # forward lean.  The TOF score is combined with min(), preventing it
        # from double-counting the camera's relative-Z lean estimate.
        delta_cm = round(self._baseline_cm - distance, 1)
        forward_penalty = min(self.max_forward_penalty, max(0.0, delta_cm - self.forward_start_cm) * self.forward_points_per_cm)
        recline_penalty = min(self.max_recline_penalty, max(0.0, -delta_cm - self.recline_start_cm) * self.recline_points_per_cm)
        penalty = round(forward_penalty + recline_penalty, 1)
        tof_score = max(0.0, 100.0 - penalty)
        result["score"] = round(min(float(result["score"]), tof_score), 1)
        result.update({
            "tof_status": "TOF400C พร้อมใช้งาน",
            "tof_baseline_cm": self._baseline_cm,
            "tof_delta_cm": delta_cm,
            "tof_penalty": penalty,
        })
        return result
