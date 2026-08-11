#!/usr/bin/env python3
"""Continuously print TOF400C / VL53L1X distance readings."""

from __future__ import annotations

import argparse
import time

from sensor_readers import SensorReadError, VL53L1X_DEFAULT_ADDRESS, Vl53l1xReader, parse_i2c_address


def main() -> int:
    parser = argparse.ArgumentParser(description="ทดสอบ TOF400C / VL53L1X")
    parser.add_argument("--address", type=parse_i2c_address, default=VL53L1X_DEFAULT_ADDRESS)
    parser.add_argument("--mode", choices=("short", "long"), default="long")
    parser.add_argument("--timing-budget", type=int, default=50, choices=(15, 20, 33, 50, 100, 200, 500))
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval ต้องมากกว่า 0")

    sensor = Vl53l1xReader(
        address=args.address,
        distance_mode=1 if args.mode == "short" else 2,
        timing_budget=args.timing_budget,
    )
    print(f"TOF400C / VL53L1X @ 0x{args.address:02x} ({args.mode} mode)")
    try:
        while True:
            try:
                print(f"Distance: {sensor.read_distance_cm():.1f} cm")
            except SensorReadError as error:
                print(f"Distance: SENSOR ERROR ({error})")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nหยุดการทดสอบเซนเซอร์")
    finally:
        sensor.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
