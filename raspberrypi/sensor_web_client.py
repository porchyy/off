#!/usr/bin/env python3
"""Read BH1750 continuously and publish its latest value."""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Any, Callable

import requests

from sensor_readers import BH1750_ADDRESSES, Bh1750Reader, SensorReadError, parse_i2c_address


def parse_lux_scale(value: str) -> float:
    try:
        scale = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("lux scale ต้องเป็นตัวเลข") from error
    if not math.isfinite(scale) or scale <= 0:
        raise argparse.ArgumentTypeError("lux scale ต้องมากกว่า 0")
    return scale


def read_sensor_payload(
    bh1750: Bh1750Reader,
) -> dict[str, float | bool | None]:
    """Read the BH1750 without failing the publisher on an I2C error."""
    lux = None
    try:
        lux = bh1750.read_lux()
    except SensorReadError:
        pass
    return {
        "lux": lux,
        "bh1750Ok": lux is not None,
    }


def publish_sensor_payload(
    endpoint: str,
    payload: dict[str, float | bool | None],
    timeout: float,
    put: Callable[..., Any] = requests.put,
) -> None:
    """Publish one reading; callers decide how and when to retry failures."""
    response = put(endpoint, json=payload, timeout=timeout)
    try:
        response.raise_for_status()
    finally:
        # Explicitly release the socket back to requests' connection pool.
        # This client runs forever, so relying on garbage collection can
        # eventually exhaust the systemd service's file descriptor limit.
        response.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ส่งค่า BH1750 ล่าสุดไปยัง OfficeGuardian dashboard"
    )
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--bh1750-address", type=parse_i2c_address, action="append")
    parser.add_argument(
        "--lux-scale",
        type=parse_lux_scale,
        default=parse_lux_scale(os.getenv("POSTUREAI_BH1750_LUX_SCALE", "1.0")),
        help="ตัวคูณปรับเทียบค่า Lux (default: 1.0)",
    )
    args = parser.parse_args()
    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval และ --timeout ต้องมากกว่า 0")

    bh_addresses = tuple(args.bh1750_address) if args.bh1750_address else BH1750_ADDRESSES
    bh1750 = Bh1750Reader(
        addresses=bh_addresses,
        bus_number=args.bus,
        lux_scale=args.lux_scale,
    )
    endpoint = f"{args.backend_url.rstrip('/')}/api/sensors/latest"

    print(f"ส่งข้อมูล sensor ไปที่ {endpoint} — กด Ctrl+C เพื่อหยุด")
    session = requests.Session()
    backend_failures = 0
    try:
        while True:
            started = time.monotonic()
            payload = read_sensor_payload(bh1750)
            try:
                publish_sensor_payload(endpoint, payload, args.timeout, session.put)
                backend_failures = 0
                lux = payload["lux"]
                print(f"Lux: {lux if lux is not None else 'SENSOR ERROR'}")
            except requests.RequestException as error:
                backend_failures += 1
                retry_seconds = min(10.0, max(args.interval, 2 ** min(backend_failures - 1, 4)))
                print(f"Backend: ERROR ({error}); retrying in {retry_seconds:g}s")
                time.sleep(max(0.0, retry_seconds - (time.monotonic() - started)))
                continue
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nหยุด sensor web client")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
