"""PostureAI Raspberry Pi client.

Main loop ที่:
  1. เปิดกล้อง
  2. จับ pose ด้วย MediaPipe
  3. คำนวณคะแนน + ส่ง sample ไป backend
  4. แจ้ง alert ถ้าคะแนนตกต่อเนื่องเกิน threshold
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
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
    for section in ("backend", "camera", "detection", "roboflow", "risk", "sound", "indicator", "buzzer", "lcd", "buffer", "video"):
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
    config["backend"]["settings_sync_seconds"] = max(5.0, float(config["backend"].get("settings_sync_seconds", 30)))

    camera = config["camera"]
    camera["backend"] = str(camera.get("backend", "auto")).lower()
    if camera["backend"] not in {"auto", "picamera2", "opencv"}:
        raise ValueError("camera.backend must be auto, picamera2, or opencv")
    for key, default in (("width", 640), ("height", 360), ("retries", 3)):
        camera[key] = int(camera.get(key, default))
        if camera[key] <= 0:
            raise ValueError(f"camera.{key} must be positive")
    camera["flip"] = int(camera.get("flip", 0))
    if camera["flip"] not in {-1, 0, 1}:
        raise ValueError("camera.flip must be -1, 0, or 1")

    detection = config["detection"]
    detection["enabled"] = bool(detection.get("enabled", True))
    mode = str(detection.get("mode", "mediapipe")).lower()
    if mode != "mediapipe":
        raise ValueError("detection.mode currently supports only mediapipe")
    detection["mode"] = mode
    detection["interval"] = max(0.1, float(detection.get("interval", 0.1)))
    detection["overlay_smoothing_alpha"] = min(
        0.95, max(0.05, float(detection.get("overlay_smoothing_alpha", 0.65)))
    )
    detection["overlay_hold_seconds"] = min(
        5.0, max(0.0, float(detection.get("overlay_hold_seconds", 0.2)))
    )
    detection["overlay_min_visibility"] = min(
        1.0, max(0.0, float(detection.get("overlay_min_visibility", 0.35)))
    )
    detection["metric_smoothing_alpha"] = min(
        0.95, max(0.05, float(detection.get("metric_smoothing_alpha", 0.35)))
    )
    model_path = Path(str(detection.get("model", "../frontend/public/models/pose_landmarker_full.task")))
    if not model_path.is_absolute():
        model_path = config_path.parent / model_path
    detection["model"] = str(model_path)

    roboflow = config["roboflow"]
    roboflow["enabled"] = bool(roboflow.get("enabled", False))
    roboflow["model_id"] = str(roboflow.get("model_id", "sitting-posture-detection-3933f/2")).strip()
    if not roboflow["model_id"]:
        raise ValueError("roboflow.model_id must not be empty")
    roboflow["interval"] = max(0.5, float(roboflow.get("interval", 1.0)))
    roboflow["confidence"] = min(1.0, max(0.0, float(roboflow.get("confidence", 0.6))))
    roboflow["timeout"] = max(1.0, float(roboflow.get("timeout", 8.0)))
    roboflow["input_width"] = max(160, min(1280, int(roboflow.get("input_width", 640))))
    roboflow["api_key_env"] = str(roboflow.get("api_key_env", "ROBOFLOW_API_KEY")).strip()
    if not roboflow["api_key_env"]:
        raise ValueError("roboflow.api_key_env must not be empty")

    video = config["video"]
    video["enabled"] = bool(video.get("enabled", True))
    video["width"] = int(video.get("width", camera["width"]))
    video["height"] = int(video.get("height", camera["height"]))
    if video["width"] <= 0 or video["height"] <= 0:
        raise ValueError("video.width and video.height must be positive")
    video["fps"] = max(1.0, min(30.0, float(video.get("fps", 12))))
    # Capture only once: the camera dimensions drive both AI and WebRTC.
    camera["width"] = video["width"]
    camera["height"] = video["height"]

    indicator = config["indicator"]
    indicator["enabled"] = bool(indicator.get("enabled", False))
    indicator["pin"] = int(indicator.get("pin", 17))
    if not 0 <= indicator["pin"] <= 27:
        raise ValueError("indicator.pin must be a BCM GPIO number from 0 to 27")
    indicator["active_high"] = bool(indicator.get("active_high", True))
    indicator["threshold"] = min(100.0, max(0.0, float(indicator.get("threshold", 50))))

    buzzer = config["buzzer"]
    buzzer["enabled"] = bool(buzzer.get("enabled", False))
    buzzer["pin"] = int(buzzer.get("pin", 27))
    if not 0 <= buzzer["pin"] <= 27:
        raise ValueError("buzzer.pin must be a BCM GPIO number from 0 to 27")
    buzzer["active_high"] = bool(buzzer.get("active_high", True))
    buzzer["threshold"] = min(100.0, max(0.0, float(buzzer.get("threshold", 50))))

    lcd = config["lcd"]
    lcd["enabled"] = bool(lcd.get("enabled", False))
    try:
        lcd["i2c_address"] = int(str(lcd.get("i2c_address", "0x27")), 0)
    except ValueError as exc:
        raise ValueError("lcd.i2c_address must be an I2C address such as 0x27") from exc
    if not 0x03 <= lcd["i2c_address"] <= 0x77:
        raise ValueError("lcd.i2c_address must be from 0x03 to 0x77")
    lcd["i2c_port"] = max(0, int(lcd.get("i2c_port", 1)))
    lcd["columns"] = min(40, max(8, int(lcd.get("columns", 16))))
    lcd["rows"] = min(4, max(1, int(lcd.get("rows", 2))))
    lcd["update_seconds"] = min(10.0, max(0.2, float(lcd.get("update_seconds", 0.5))))
    lcd["risk_threshold"] = min(99.0, max(1.0, float(lcd.get("risk_threshold", config["risk"].get("threshold", 60)))))

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
    parser.add_argument("--test-led", action="store_true", help="Blink the configured red LED twice and exit")
    parser.add_argument("--test-buzzer", action="store_true", help="Beep the configured buzzer 3 times and exit")
    parser.add_argument("--test-lcd", action="store_true", help="Show a sample score on the configured LCD 1602 and exit")
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
    from client.buzzer import GpioBuzzer
    from client.indicator import GpioLed
    from client.lcd import CharacterLcd

    sound_player = SoundPlayer(config.get("sound", {}))
    indicator = GpioLed(config.get("indicator", {}))
    buzzer = GpioBuzzer(config.get("buzzer", {}))
    lcd = CharacterLcd(config.get("lcd", {}))
    if args.test_sound:
        logger.info("testing alert sound...")
        return 0 if sound_player.play() else 1
    if args.test_led:
        logger.info("testing red LED indicator: blinking twice...")
        return 0 if indicator.blink(times=2) else 1
    if args.test_buzzer:
        logger.info("testing buzzer: beeping 3 times...")
        result = buzzer.beep(times=3)
        buzzer.close()
        return 0 if result else 1
    if args.test_lcd:
        logger.info("testing LCD 1602 with a sample score for 3 seconds...")
        shown = lcd.show_test()
        time.sleep(3)
        lcd.close()
        return 0 if shown else 1

    from client.capture import open_camera

    if args.check:
        camera = None
        try:
            import requests

            if config["detection"]["enabled"]:
                from client.detect import close_detector, get_detector

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
            detector_name = "MediaPipe, " if config["detection"]["enabled"] else ""
            logger.info("self-check OK: %s%s camera, and backend are ready", detector_name, camera.backend)
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
            if config["detection"]["enabled"]:
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

    from client.capture import CameraProducer
    from client.roboflow import RoboflowInferenceWorker
    from client.uploader import Uploader
    from client.webrtc import PiWebRtcSender

    detection_enabled = config["detection"]["enabled"]
    if detection_enabled:
        from client.detect import close_detector, draw_pose_overlay, process_live_frame
    else:
        # Keep the MediaPipe code installed for easy rollback, but do not load
        # its model or call its inference path in Roboflow-only mode.
        close_detector = lambda: None

    backend_url = config["backend"]["url"]
    uploader = Uploader(
        url=backend_url,
        timeout=config["backend"].get("timeout", 5),
        buffer_path=config["buffer"]["path"],
    )
    alert_controller = AlertController(config, uploader, sound_player, indicator, buzzer)
    roboflow = RoboflowInferenceWorker(config["roboflow"])

    consecutive_failures = 0
    camera = None
    producer = None
    webrtc = None
    once_deadline = time.monotonic() + 5 if args.once else None
    last_settings_sync = 0.0
    try:
        camera = open_camera(config["camera"])
        producer = CameraProducer(camera, config["video"]["fps"])

        if detection_enabled:
            def update_stream_overlay(landmarks: list[dict[str, Any]], metrics: dict[str, Any] | None) -> None:
                if not landmarks:
                    producer.set_overlay_renderer(None)
                    return
                landmark_snapshot = [dict(point) for point in landmarks]
                metrics_snapshot = dict(metrics) if metrics else None
                min_visibility = config["detection"]["overlay_min_visibility"]
                producer.set_overlay_renderer(
                    lambda image: draw_pose_overlay(image, landmark_snapshot, metrics_snapshot, min_visibility)
                )
        else:
            update_stream_overlay = None
            logger.info("MediaPipe is disabled; running Roboflow posture classification only")

        producer.start()
        if config["video"]["enabled"]:
            webrtc = PiWebRtcSender(
                producer.frames, backend_url, config["video"]["fps"], producer.color_space, camera.stream_format
            )
            webrtc.start()
        while True:
            try:
                now = time.monotonic()
                if now - last_settings_sync >= config["backend"]["settings_sync_seconds"]:
                    remote_settings = uploader.fetch_settings()
                    if remote_settings is None:
                        uploader.send_client_status(online=False, last_sync_at=None, message="backend settings unavailable; using last known values")
                    else:
                        alert_controller.apply_runtime_settings(remote_settings)
                        uploader.send_client_status(
                            online=True,
                            last_sync_at=datetime.now(timezone.utc).isoformat(),
                            message="dashboard settings synchronized",
                        )
                    last_settings_sync = now
                frame, _ = producer.frames.get()
                if frame is not None:
                    if detection_enabled:
                        process_live_frame(
                            frame,
                            config,
                            uploader,
                            alert_controller,
                            producer.color_space,
                            webrtc.publish_pose if webrtc else None,
                            update_stream_overlay,
                            lcd,
                        )
                    roboflow.submit_if_due(frame, producer.color_space)
                    classification = roboflow.take_result()
                    if classification is not None and webrtc is not None:
                        webrtc.publish_roboflow_result(classification)
                consecutive_failures = producer.failures
                if consecutive_failures >= 3:
                    raise RuntimeError(f"camera capture failed repeatedly: {producer.last_error}")
            except Exception as exc:
                consecutive_failures += 1
                logger.error("detection cycle error (failure %s): %s", consecutive_failures, exc)
                if consecutive_failures >= 3:
                    logger.warning("re-opening camera after %s consecutive failures...", consecutive_failures)
                    try:
                        if producer:
                            producer.stop()
                        if camera:
                            camera.release()
                    except Exception:
                        pass
                    time.sleep(2)
                    camera = open_camera(config["camera"])
                    producer = CameraProducer(camera, config["video"]["fps"])
                    producer.start()
                    if webrtc:
                        webrtc.stop()
                        webrtc = PiWebRtcSender(
                            producer.frames, backend_url, config["video"]["fps"], producer.color_space, camera.stream_format
                        )
                        webrtc.start()
                    consecutive_failures = 0

            if args.once and frame is not None:
                break
            if once_deadline is not None and time.monotonic() >= once_deadline:
                logger.error("camera did not provide a live frame within 5 seconds")
                return 1
            time.sleep(0.02)
    finally:
        if webrtc:
            webrtc.stop()
        if producer:
            producer.stop()
        if camera:
            try:
                camera.release()
            except Exception:
                pass
        roboflow.stop()
        close_detector()
        indicator.close()
        buzzer.close()
        lcd.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
