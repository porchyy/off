"""GPIO buzzer for the PostureAI Raspberry Pi client."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GpioBuzzer:
    """Control a passive/active buzzer module via GPIO.

    Works identically to GpioLed but drives a buzzer instead.
    When enabled, the buzzer sounds when the posture score drops
    below the configured threshold (default 50).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.pin = int(config.get("pin", 27))
        self.active_high = bool(config.get("active_high", True))
        self.threshold = min(100.0, max(0.0, float(config.get("threshold", 50))))
        self._buzzer: Any | None = None
        self._is_on = False

        if not self.enabled:
            return
        if not 0 <= self.pin <= 27:
            raise ValueError("buzzer.pin must be a BCM GPIO number from 0 to 27")
        try:
            from gpiozero import LED  # type: ignore  # LED works for active buzzers too

            self._buzzer = LED(self.pin, active_high=self.active_high, initial_value=False)
            logger.info("buzzer ready on BCM GPIO%s (threshold=%s)", self.pin, self.threshold)
        except Exception as exc:
            logger.error("buzzer is unavailable: %s", exc)

    def on(self) -> bool:
        if self._buzzer is None:
            return False
        try:
            self._buzzer.on()
            self._is_on = True
            return True
        except Exception as exc:
            logger.error("could not turn on buzzer: %s", exc)
            return False

    def off(self) -> bool:
        if self._buzzer is None:
            return False
        try:
            self._buzzer.off()
            self._is_on = False
            return True
        except Exception as exc:
            logger.error("could not turn off buzzer: %s", exc)
            return False

    def beep(self, times: int = 3, on_seconds: float = 0.15, off_seconds: float = 0.1) -> bool:
        """Sound the buzzer a bounded number of times, then leave it off."""
        beeps = max(1, int(times))
        on_duration = max(0.0, float(on_seconds))
        off_duration = max(0.0, float(off_seconds))

        for index in range(beeps):
            if not self.on():
                self.off()
                return False
            time.sleep(on_duration)
            self.off()
            if index < beeps - 1:
                time.sleep(off_duration)
        return True

    def update(self, score: float) -> None:
        """Turn buzzer on/off based on posture score threshold."""
        should_buzz = score < self.threshold
        if should_buzz and not self._is_on:
            self.on()
        elif not should_buzz and self._is_on:
            self.off()

    def close(self) -> None:
        """Leave the buzzer off when the client exits or restarts."""
        if self._buzzer is not None:
            self.off()
            self._buzzer.close()
            self._buzzer = None
