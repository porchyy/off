"""PostureAI Raspberry Pi client.

Skeleton — main loop ที่:
  1. เปิดกล้อง
  2. จับ pose ด้วย MediaPipe
  3. คำนวณคะแนน + ส่ง sample ไป backend
  4. แจ้ง alert ถ้าคะแนนตกต่อเนื่องเกิน threshold

TODO: port logic จาก frontend/app.js (MediaPipe Pose ใน browser) มาเป็น
Python เวอร์ชัน
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("postureai")


def load_config(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("config root must be a YAML mapping")
    return config


def validate_config(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """Validate the small stable configuration surface before opening hardware."""
    for section in ("backend", "camera", "detection", "risk", "sound", "buffer", "stream"):
        value = config.get(section)
        if value is None:
            config[section] = {}
        elif not isinstance(value, dict):
            raise ValueError(f"{section} must be a mapping")

    backend_url = config["backend"].get("url", "http://localhost:8000")
    if not isinstance(backend_url, str) or not backend_url.startswith(("http://", "https://")):
        raise ValueError("backend.url must start with http:// or https://")
    config["backend"]["url"] = backend_url.rstrip("/")
    config["backend"]["timeout"] = max(1.0, float(config["backend"].get("timeout", 5)))

    camera = config["camera"]
    camera["backend"] = str(camera.get("backend", "auto")).lower()
    if camera["backend"] not in {"auto", "picamera2", "opencv"}:
        raise ValueError("camera.backend must be auto, picamera2, or opencv")
    for key, default in (("width", 640), ("height", 480), ("retries", 3)):
        camera[key] = int(camera.get(key, default))
        if camera[key] <= 0:
            raise ValueError(f"camera.{key} must be positive")
    camera["flip"] = int(camera.get("flip", 0))
    if camera["flip"] not in {-1, 0, 1}:
        raise ValueError("camera.flip must be -1, 0, or 1")

    detection = config["detection"]
    mode = str(detection.get("mode", "mediapipe")).lower()
    if mode != "mediapipe":
        raise ValueError("detection.mode currently supports only mediapipe")
    detection["mode"] = mode
    detection["interval"] = max(0.1, float(detection.get("interval", 5)))
    model_path = Path(str(detection.get("model", "../frontend/public/models/pose_landmarker_full.task")))
    if not model_path.is_absolute():
        model_path = config_path.parent / model_path
    detection["model"] = str(model_path)

    stream = config["stream"]
    stream["enabled"] = bool(stream.get("enabled", True))
    stream["interval"] = max(0.1, float(stream.get("interval", 0.2)))
    stream["quality"] = max(30, min(95, int(stream.get("quality", 80))))

    buffer_path = Path(str(config["buffer"].get("path", "buffer.sqlite")))
    if not buffer_path.is_absolute():
        buffer_path = config_path.parent / buffer_path
    config["buffer"]["path"] = str(buffer_path)
    return config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PostureAI Pi client")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--once", action="store_true", help="Run a single detection cycle and exit (for testing)")
    parser.add_argument("--test-sound", action="store_true", help="Play the configured alert sound and exit")
    parser.add_argument("--test-camera", action="store_true", help="Capture one frame without backend or pose detection")
    parser.add_argument("--check", action="store_true", help="Check MediaPipe, camera, and backend connectivity, then exit")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.config.exists():
        logger.error("config not found: %s (copy config.example.yaml first)", args.config)
        return 2

    try:
        config = validate_config(load_config(args.config), args.config.resolve())
    except (OSError, ValueError, TypeError) as exc:
        logger.error("invalid config: %s", exc)
        return 2
    logger.info("loaded config from %s", args.config)

    # Lazy imports so --help / config validation ไม่ต้องมี lib ติดตั้งครบ
    from client.alert import AlertController, SoundPlayer

    sound_player = SoundPlayer(config.get("sound", {}))
    if args.test_sound:
        logger.info("testing alert sound...")
        return 0 if sound_player.play() else 1

    from client.capture import open_camera

    if args.check:
        camera = None
        try:
            from client.detect import close_detector, get_detector
            import requests

            get_detector(config["detection"]["model"])
            camera = open_camera(config["camera"])
            ok, frame = camera.read()
            if not ok or frame is None:
                logger.error("camera opened but no frame was received")
                return 1
            response = requests.get(f"{config['backend']['url']}/api/health", timeout=config["backend"]["timeout"])
            if not response.ok:
                logger.error("backend health check returned %s", response.status_code)
                return 1
            logger.info("self-check OK: MediaPipe, %s camera, and backend are ready", camera.backend)
            return 0
        except Exception as exc:
            logger.error("self-check failed: %s", exc)
            return 1
        finally:
            if camera:
                try:
                    camera.release()
                except Exception as exc:
                    logger.warning("could not release camera after self-check: %s", exc)
            close_detector()

    if args.test_camera:
        camera = None
        try:
            camera = open_camera(config["camera"])
            ok, frame = camera.read()
            if not ok or frame is None:
                logger.error("camera opened but no frame was received")
                return 1
            logger.info("camera sensor OK: backend=%s frame=%sx%s", camera.backend, frame.shape[1], frame.shape[0])
            return 0
        finally:
            if camera:
                camera.release()

    from client.detect import close_detector, run_detection_cycle
    from client.uploader import Uploader

    backend_url = config["backend"]["url"]
    uploader = Uploader(
        url=backend_url,
        timeout=config["backend"].get("timeout", 5),
        buffer_path=config["buffer"]["path"],
    )
    alert_controller = AlertController(config, uploader, sound_player)

    consecutive_failures = 0
    camera = None
    try:
        camera = open_camera(config["camera"])
        while True:
            try:
                run_detection_cycle(camera, config, uploader, alert_controller)
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                logger.error("detection cycle error (failure %s): %s", consecutive_failures, exc)
                if consecutive_failures >= 3:
                    logger.warning("re-opening camera after %s consecutive failures...", consecutive_failures)
                    try:
                        if camera:
                            camera.release()
                    except Exception:
                        pass
                    time.sleep(2)
                    camera = open_camera(config["camera"])
                    consecutive_failures = 0

            if args.once:
                break
            time.sleep(config.get("stream", {}).get("interval", 0.2))
    finally:
        if camera:
            try:
                camera.release()
            except Exception:
                pass
        close_detector()
    return 0


if __name__ == "__main__":
    sys.exit(main())
