"""In-memory latest readings received from the Raspberry Pi sensor client."""

from __future__ import annotations

from datetime import datetime, timezone


class SensorStore:
    def __init__(self) -> None:
        self.lux: float | None = None
        self.bh1750_ok = False
        self.distance_cm: float | None = None
        self.vl53l1x_ok = False
        self.updated_at: str | None = None

    def update(
        self,
        *,
        lux: float | None,
        bh1750_ok: bool,
        distance_cm: float | None,
        vl53l1x_ok: bool,
    ) -> None:
        self.lux = lux
        self.bh1750_ok = bh1750_ok
        self.distance_cm = distance_cm
        self.vl53l1x_ok = vl53l1x_ok
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, float | bool | str | None]:
        return {
            "lux": self.lux,
            "bh1750_ok": self.bh1750_ok,
            "distance_cm": self.distance_cm,
            "vl53l1x_ok": self.vl53l1x_ok,
            "updated_at": self.updated_at,
        }


sensor_store = SensorStore()
