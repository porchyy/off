#!/usr/bin/env python3
"""Read BH1750/TOF200C continuously and publish only their latest values."""

from __future__ import annotations

import argparse
import time

import requests

from sensor_readers import (
    BH1750_ADDRESSES,
    Bh1750Reader,
    SensorReadError,
    Tof200cReader,
    parse_i2c_address,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ส่งค่า BH1750 และ TOF200C ล่าสุดไปยัง OfficeGuardian dashboard"
    )
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--bh1750-address", type=parse_i2c_address, action="append")
    parser.add_argument("--tof200c-address", type=parse_i2c_address, default=0x29)
    args = parser.parse_args()
    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval และ --timeout ต้องมากกว่า 0")

    bh_addresses = tuple(args.bh1750_address) if args.bh1750_address else BH1750_ADDRESSES
    bh1750 = Bh1750Reader(addresses=bh_addresses, bus_number=args.bus)
    tof200c = Tof200cReader(address=args.tof200c_address, bus_number=args.bus)
    endpoint = f"{args.backend_url.rstrip('/')}/api/sensors/latest"

    print(f"ส่งข้อมูล sensor ไปที่ {endpoint} — กด Ctrl+C เพื่อหยุด")
    try:
        while True:
            started = time.monotonic()
            lux = None
            distance_cm = None
            try:
                lux = bh1750.read_lux()
            except SensorReadError:
                pass
            try:
                distance_cm = tof200c.read_distance_cm()
            except SensorReadError:
                pass

            payload = {
                "lux": lux,
                "distanceCm": distance_cm,
                "bh1750Ok": lux is not None,
                "tof200cOk": distance_cm is not None,
            }
            try:
                response = requests.put(endpoint, json=payload, timeout=args.timeout)
                response.raise_for_status()
                print(
                    f"Lux: {lux if lux is not None else 'SENSOR ERROR'} | "
                    f"Distance: {f'{distance_cm:.1f} cm' if distance_cm is not None else 'SENSOR ERROR'}"
                )
            except requests.RequestException as error:
                print(f"Backend: ERROR ({error})")
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nหยุด sensor web client")
    finally:
        tof200c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
