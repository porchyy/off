"""GPIO status indicator for the OffSyn Tech Raspberry Pi client."""

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
        self._lgpio: Any | None = None
        self._lgpio_handle: int | None = None
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
            if self._initialize_lgpio_fallback():
                return
            # Posture monitoring must keep working if a non-essential LED is
            # disconnected or this client is run outside a Raspberry Pi.
            logger.error("red LED indicator is unavailable: %s", exc)

    def _initialize_lgpio_fallback(self) -> bool:
        """Use lgpio directly when gpiozero cannot open a Pi 5 GPIO chip."""
        if self.chip is None:
            return False
        handle: int | None = None
        try:
            import lgpio  # type: ignore

            handle = lgpio.gpiochip_open(self.chip)
            inactive_level = 0 if self.active_high else 1
            lgpio.gpio_claim_output(handle, self.pin, inactive_level)
            self._lgpio = lgpio
            self._lgpio_handle = handle
            logger.info("red LED indicator ready on BCM GPIO%s via direct gpiochip%s", self.pin, self.chip)
            return True
        except Exception as exc:
            if handle is not None:
                try:
                    lgpio.gpiochip_close(handle)
                except Exception:
                    pass
            logger.debug("direct lgpio LED fallback is unavailable: %s", exc)
            return False

    def on(self) -> bool:
        try:
            if self._led is not None:
                self._led.on()
            elif self._lgpio is not None and self._lgpio_handle is not None:
                self._lgpio.gpio_write(
                    self._lgpio_handle, self.pin, 1 if self.active_high else 0
                )
            else:
                return False
            self._is_on = True
            return True
        except Exception as exc:
            logger.error("could not turn on red LED: %s", exc)
            return False

    def off(self) -> bool:
        try:
            if self._led is not None:
                self._led.off()
            elif self._lgpio is not None and self._lgpio_handle is not None:
                self._lgpio.gpio_write(
                    self._lgpio_handle, self.pin, 0 if self.active_high else 1
                )
            else:
                return False
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
        if self._lgpio is not None and self._lgpio_handle is not None:
            self.off()
            self._lgpio.gpio_free(self._lgpio_handle, self.pin)
            self._lgpio.gpiochip_close(self._lgpio_handle)
            self._lgpio_handle = None
            self._lgpio = None
