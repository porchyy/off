"""In-memory latest readings received from the Raspberry Pi sensor client."""

from __future__ import annotations

from datetime import datetime, timezone


class SensorStore:
    def __init__(self) -> None:
        self.lux: float | None = None
        self.distance_cm: float | None = None
        self.bh1750_ok = False
        self.tof200c_ok = False
        self.updated_at: str | None = None

    def update(
        self,
        *,
        lux: float | None,
        distance_cm: float | None,
        bh1750_ok: bool,
        tof200c_ok: bool,
    ) -> None:
        self.lux = lux
        self.distance_cm = distance_cm
        self.bh1750_ok = bh1750_ok
        self.tof200c_ok = tof200c_ok
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, float | bool | str | None]:
        return {
            "lux": self.lux,
            "distance_cm": self.distance_cm,
            "bh1750_ok": self.bh1750_ok,
            "tof200c_ok": self.tof200c_ok,
            "updated_at": self.updated_at,
        }


sensor_store = SensorStore()
