"""Optional 16x2 I2C character LCD output for PostureAI."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CharacterLcd:
    """Show the current posture score on a HD44780-compatible I2C LCD.

    The display is intentionally best-effort: a disconnected LCD must never
    stop the camera, MediaPipe, dashboard, or alert loop.
    """

    def __init__(self, config: dict[str, Any], clock: Callable[[], float] = time.monotonic) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.address = int(config.get("i2c_address", 0x27))
        self.port = int(config.get("i2c_port", 1))
        self.cols = int(config.get("columns", 16))
        self.rows = int(config.get("rows", 2))
        self.update_seconds = max(0.2, float(config.get("update_seconds", 0.5)))
        self.risk_threshold = float(config.get("risk_threshold", 60))
        self._clock = clock
        self._lcd: Any | None = None
        self._last_lines: tuple[str, str] | None = None
        self._last_write_at = 0.0

        if not self.enabled:
            return
        try:
            from RPLCD.i2c import CharLCD  # type: ignore

            self._lcd = CharLCD(
                "PCF8574",
                address=self.address,
                port=self.port,
                cols=self.cols,
                rows=self.rows,
                charmap="A00",
                auto_linebreaks=False,
            )
            self._write(("POSTUREAI READY", "WAITING FOR POSE"), force=True)
            logger.info("LCD 1602 ready on I2C bus %s address 0x%02X", self.port, self.address)
        except Exception as exc:
            logger.error("LCD 1602 is unavailable: %s", exc)

    @staticmethod
    def _fit(text: str, columns: int) -> str:
        # Common HD44780 character sets cannot render Thai reliably, so the
        # physical screen uses short ASCII labels while the web stays Thai.
        return text.encode("ascii", "replace").decode("ascii")[:columns].center(columns)

    @classmethod
    def format_metrics(cls, metrics: dict[str, Any], *, columns: int, risk_threshold: float) -> tuple[str, str]:
        score = max(0, min(100, round(float(metrics["score"]))))
        if score >= 70:
            status = "GOOD POSTURE"
        elif score >= 40:
            status = "CHECK POSTURE"
        else:
            status = "ADJUST POSTURE"
        return cls._fit(f"SCORE: {score:3}/100", columns), cls._fit(status, columns)

    @property
    def available(self) -> bool:
        return self._lcd is not None

    def _write(self, lines: tuple[str, str], *, force: bool = False) -> bool:
        if self._lcd is None:
            return False
        now = self._clock()
        if not force and lines == self._last_lines and now - self._last_write_at < self.update_seconds:
            return True
        try:
            self._lcd.cursor_pos = (0, 0)
            self._lcd.write_string(lines[0])
            self._lcd.cursor_pos = (1, 0)
            self._lcd.write_string(lines[1])
            self._last_lines = lines
            self._last_write_at = now
            return True
        except Exception as exc:
            logger.error("could not update LCD 1602: %s", exc)
            return False

    def show_metrics(self, metrics: dict[str, Any]) -> bool:
        lines = self.format_metrics(metrics, columns=self.cols, risk_threshold=self.risk_threshold)
        return self._write(lines)

    def show_test(self) -> bool:
        return self._write((self._fit("SCORE:  82/100", self.cols), self._fit("GOOD POSTURE", self.cols)), force=True)

    def close(self) -> None:
        if self._lcd is None:
            return
        try:
            self._lcd.clear()
            self._lcd.close(clear=True)
        except Exception as exc:
            logger.warning("could not close LCD 1602 cleanly: %s", exc)
        finally:
            self._lcd = None
