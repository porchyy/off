"""Local audible alerts for the Raspberry Pi client."""

from __future__ import annotations

import logging
import math
import shutil
import struct
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SoundPlayer:
    """Play a WAV file through ALSA, or generate a short two-tone beep."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", True))
        self.device = str(config.get("device", "default"))
        self.file = config.get("file")
        self.volume = max(0.0, min(1.0, float(config.get("volume", 0.75))))

    def play(self) -> bool:
        if not self.enabled:
            logger.debug("sound alert is disabled")
            return False

        player = shutil.which("aplay")
        if not player:
            logger.error("cannot play alert: aplay not found (install package alsa-utils)")
            return False

        temporary_path: Path | None = None
        try:
            if self.file:
                sound_path = Path(str(self.file)).expanduser()
                if not sound_path.is_file():
                    logger.error("alert sound file not found: %s", sound_path)
                    return False
            else:
                temporary_path = self._make_beep()
                sound_path = temporary_path

            command = [player, "-q"]
            if self.device:
                command.extend(["-D", self.device])
            command.append(str(sound_path))
            result = subprocess.run(command, check=False, timeout=10)
            if result.returncode != 0:
                logger.error("aplay exited with status %s (device=%s)", result.returncode, self.device)
                return False
            return True
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("failed to play alert sound: %s", exc)
            return False
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)

    def _make_beep(self) -> Path:
        sample_rate = 44_100
        segments = ((880.0, 0.22), (0.0, 0.10), (1_100.0, 0.28))
        samples: list[int] = []
        amplitude = int(32767 * self.volume)
        for frequency, duration in segments:
            count = int(sample_rate * duration)
            for index in range(count):
                # Short fades prevent clicks at the beginning and end of each tone.
                fade = min(1.0, index / 400, (count - index) / 400)
                value = 0 if frequency == 0 else int(amplitude * fade * math.sin(2 * math.pi * frequency * index / sample_rate))
                samples.append(value)

        handle = tempfile.NamedTemporaryFile(prefix="postureai-alert-", suffix=".wav", delete=False)
        handle.close()
        path = Path(handle.name)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        return path


class AlertController:
    """Trigger one alert after a low score persists, with a repeat cooldown."""

    def __init__(
        self,
        config: dict[str, Any],
        uploader: Any,
        sound_player: SoundPlayer,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        risk = config.get("risk", {})
        self.threshold = float(risk.get("threshold", 60))
        self.risk_seconds = max(0.0, float(risk.get("seconds", 45)))
        self.cooldown = max(0.0, float(risk.get("cooldown", 30)))
        self.uploader = uploader
        self.sound_player = sound_player
        self.clock = clock
        self.low_since: float | None = None
        self.last_alert: float | None = None

    def update(self, metrics: dict[str, float]) -> bool:
        now = self.clock()
        score = float(metrics["score"])
        if score >= self.threshold:
            self.low_since = None
            return False

        if self.low_since is None:
            self.low_since = now
        if now - self.low_since < self.risk_seconds:
            return False
        if self.last_alert is not None and now - self.last_alert < self.cooldown:
            return False

        self.last_alert = now
        logger.warning("posture risk persisted for %.1fs (score %.1f < %.1f)", now - self.low_since, score, self.threshold)
        self.sound_player.play()
        self.uploader.send_alert({
            "severity": "risk",
            "message": f"ตรวจพบท่านั่งที่ควรปรับ (คะแนน {score:g})",
        })
        return True
