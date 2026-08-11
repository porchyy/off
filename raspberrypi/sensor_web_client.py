#!/usr/bin/env python3
"""Read BH1750 continuously and publish its latest value."""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Any, Callable

import requests

from sensor_readers import (
    BH1750_ADDRESSES,
    Bh1750Reader,
    SensorReadError,
    VL53L1X_DEFAULT_ADDRESS,
    Vl53l1xReader,
    parse_i2c_address,
)


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
    vl53l1x: Vl53l1xReader | None = None,
) -> dict[str, float | bool | None]:
    """Read available environment and distance sensors without failing either."""
    lux = None
    distance_cm = None
    try:
        lux = bh1750.read_lux()
    except SensorReadError:
        pass
    if vl53l1x is not None:
        try:
            distance_cm = vl53l1x.read_distance_cm()
        except SensorReadError:
            pass
    return {
        "lux": lux,
        "bh1750Ok": lux is not None,
        "distanceCm": distance_cm,
        "vl53l1xOk": distance_cm is not None,
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
    parser.add_argument("--disable-vl53l1x", action="store_true", help="ไม่อ่าน TOF400C / VL53L1X")
    parser.add_argument("--vl53l1x-address", type=parse_i2c_address, default=VL53L1X_DEFAULT_ADDRESS)
    # Short mode เหมาะกับการทดสอบระยะใกล้รอบโต๊ะทำงาน.
    parser.add_argument("--vl53l1x-mode", choices=("short", "long"), default="short")
    parser.add_argument("--vl53l1x-timing-budget", type=int, default=50, choices=(15, 20, 33, 50, 100, 200, 500))
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
    vl53l1x = None if args.disable_vl53l1x else Vl53l1xReader(
        address=args.vl53l1x_address,
        distance_mode=1 if args.vl53l1x_mode == "short" else 2,
        timing_budget=args.vl53l1x_timing_budget,
    )
    endpoint = f"{args.backend_url.rstrip('/')}/api/sensors/latest"

    print(f"ส่งข้อมูล sensor ไปที่ {endpoint} — กด Ctrl+C เพื่อหยุด")
    session = requests.Session()
    backend_failures = 0
    try:
        while True:
            started = time.monotonic()
            payload = read_sensor_payload(bh1750, vl53l1x)
            try:
                publish_sensor_payload(endpoint, payload, args.timeout, session.put)
                backend_failures = 0
                lux = payload["lux"]
                distance_cm = payload["distanceCm"]
                print(f"Lux: {lux if lux is not None else 'SENSOR ERROR'} | Distance: {distance_cm if distance_cm is not None else 'SENSOR ERROR'} cm")
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
        if vl53l1x is not None:
            vl53l1x.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
