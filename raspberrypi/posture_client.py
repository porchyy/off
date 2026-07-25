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

import yaml

logger = logging.getLogger("postureai")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PostureAI Pi client")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--once", action="store_true", help="Run a single detection cycle and exit (for testing)")
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

    config = load_config(args.config)
    logger.info("loaded config from %s", args.config)

    # Lazy imports so --help / config validation ไม่ต้องมี lib ติดตั้งครบ
    from client.capture import open_camera
    from client.detect import run_detection_cycle
    from client.uploader import Uploader

    backend_url = config["backend"]["url"]
    uploader = Uploader(url=backend_url, timeout=config["backend"].get("timeout", 5))

    camera = open_camera(config["camera"])
    try:
        while True:
            run_detection_cycle(camera, config, uploader)
            if args.once:
                break
            time.sleep(config["detection"]["interval"])
    finally:
        camera.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
