#!/usr/bin/env python3
"""Continuously print TOF200C distance readings in centimeters."""

from __future__ import annotations

import argparse
import time

from sensor_readers import SensorReadError, Tof200cReader, parse_i2c_address


def main() -> int:
    parser = argparse.ArgumentParser(description="ทดสอบ TOF200C ผ่าน I2C")
    parser.add_argument(
        "--address",
        type=parse_i2c_address,
        default=0x29,
        help="I2C address (default: 0x29)",
    )
    parser.add_argument("--bus", type=int, default=1, help="I2C bus (default: 1)")
    parser.add_argument(
        "--interval", type=float, default=1.0, help="ช่วงเวลาอ่านค่าเป็นวินาที (default: 1)"
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval ต้องมากกว่า 0")

    reader = Tof200cReader(address=args.address, bus_number=args.bus)
    print("TOF200C continuous reader — กด Ctrl+C เพื่อหยุด")

    try:
        while True:
            started = time.monotonic()
            try:
                distance_cm = reader.read_distance_cm()
                print("\nTOF200C")
                print(f"Distance: {distance_cm:.1f} cm")
            except SensorReadError:
                print("\nTOF200C: SENSOR ERROR")
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nหยุดการทดสอบ TOF200C")
    finally:
        reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
