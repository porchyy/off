"""GPIO status indicator for the PostureAI Raspberry Pi client."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GpioLed:
    """Control a single LED module without making GPIO a hard dependency.

    The module is intentionally optional: on a development computer, or when
    disabled in config, all calls are harmless no-ops.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.pin = int(config.get("pin", 17))
        self.active_high = bool(config.get("active_high", True))
        self._led: Any | None = None
        self._is_on = False

        if not self.enabled:
            return
        if not 0 <= self.pin <= 27:
            raise ValueError("indicator.pin must be a BCM GPIO number from 0 to 27")
        try:
            from gpiozero import LED  # type: ignore

            self._led = LED(self.pin, active_high=self.active_high, initial_value=False)
            logger.info("red LED indicator ready on BCM GPIO%s", self.pin)
        except Exception as exc:
            # Posture monitoring must keep working if a non-essential LED is
            # disconnected or this client is run outside a Raspberry Pi.
            logger.error("red LED indicator is unavailable: %s", exc)

    def on(self) -> bool:
        if self._led is None:
            return False
        try:
            self._led.on()
            self._is_on = True
            return True
        except Exception as exc:
            logger.error("could not turn on red LED: %s", exc)
            return False

    def off(self) -> bool:
        if self._led is None:
            return False
        try:
            self._led.off()
            self._is_on = False
            return True
        except Exception as exc:
            logger.error("could not turn off red LED: %s", exc)
            return False

    def blink(self, times: int = 2, on_seconds: float = 0.25, off_seconds: float = 0.25) -> bool:
        """Flash the LED a bounded number of times, then leave it off."""
        flashes = max(1, int(times))
        on_duration = max(0.0, float(on_seconds))
        off_duration = max(0.0, float(off_seconds))

        for index in range(flashes):
            if not self.on():
                self.off()
                return False
            time.sleep(on_duration)
            self.off()
            if index < flashes - 1:
                time.sleep(off_duration)
        return True

    def close(self) -> None:
        """Leave the physical alert off when the client exits or restarts."""
        if self._led is not None:
            self.off()
            self._led.close()
            self._led = None
