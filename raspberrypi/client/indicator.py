"""GPIO status indicator for the PostureAI Raspberry Pi client."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _detect_lgpio_chip(sys_gpio_root: Path = Path("/sys/class/gpio")) -> int | None:
    """Return the RP1 GPIO chip number when running on a Raspberry Pi 5."""
    try:
        for chip_path in sys_gpio_root.glob("gpiochip*"):
            label = (chip_path / "label").read_text(encoding="utf-8").strip()
            if label == "pinctrl-rp1":
                return int(chip_path.name.removeprefix("gpiochip"))
    except (OSError, ValueError):
        pass
    return None


class GpioLed:
    """Control a single LED module without making GPIO a hard dependency.

    The module is intentionally optional: on a development computer, or when
    disabled in config, all calls are harmless no-ops.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.pin = int(config.get("pin", 17))
        self.active_high = bool(config.get("active_high", True))
        configured_chip = config.get("chip")
        self.chip = int(configured_chip) if configured_chip is not None else _detect_lgpio_chip()
        self._led: Any | None = None
        self._pin_factory: Any | None = None
        self._is_on = False

        if not self.enabled:
            return
        if not 0 <= self.pin <= 27:
            raise ValueError("indicator.pin must be a BCM GPIO number from 0 to 27")
        try:
            from gpiozero import LED  # type: ignore

            if self.chip is not None:
                from gpiozero.pins.lgpio import LGPIOFactory  # type: ignore

                self._pin_factory = LGPIOFactory(chip=self.chip)
            self._led = LED(
                self.pin,
                active_high=self.active_high,
                initial_value=False,
                pin_factory=self._pin_factory,
            )
            chip_detail = f" via gpiochip{self.chip}" if self.chip is not None else ""
            logger.info("red LED indicator ready on BCM GPIO%s%s", self.pin, chip_detail)
        except Exception as exc:
            if self._pin_factory is not None:
                self._pin_factory.close()
                self._pin_factory = None
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
        if self._pin_factory is not None:
            self._pin_factory.close()
            self._pin_factory = None
