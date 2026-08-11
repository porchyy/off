"""In-memory latest readings received from the Raspberry Pi sensor client."""

from __future__ import annotations

from datetime import datetime, timezone


class SensorStore:
    def __init__(self) -> None:
        self.lux: float | None = None
        self.bh1750_ok = False
        self.updated_at: str | None = None

    def update(
        self,
        *,
        lux: float | None,
        bh1750_ok: bool,
    ) -> None:
        self.lux = lux
        self.bh1750_ok = bh1750_ok
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, float | bool | str | None]:
        return {
            "lux": self.lux,
            "bh1750_ok": self.bh1750_ok,
            "updated_at": self.updated_at,
        }


sensor_store = SensorStore()
