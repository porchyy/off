#!/usr/bin/env python3
"""Continuously print BH1750 brightness readings in lux."""

from __future__ import annotations

import argparse
import math
import time

from sensor_readers import BH1750_ADDRESSES, Bh1750Reader, SensorReadError, parse_i2c_address


def parse_lux_scale(value: str) -> float:
    try:
        scale = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("lux scale ต้องเป็นตัวเลข") from error
    if not math.isfinite(scale) or scale <= 0:
        raise argparse.ArgumentTypeError("lux scale ต้องมากกว่า 0")
    return scale


def main() -> int:
    parser = argparse.ArgumentParser(description="ทดสอบ BH1750 ผ่าน I2C")
    parser.add_argument(
        "--address",
        type=parse_i2c_address,
        action="append",
        help="I2C address ที่ต้องการลอง (ระบุซ้ำได้; default: 0x23, 0x5C)",
    )
    parser.add_argument("--bus", type=int, default=1, help="I2C bus (default: 1)")
    parser.add_argument(
        "--lux-scale", type=parse_lux_scale, default=1.0, help="ตัวคูณปรับเทียบค่า Lux (default: 1.0)"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="ช่วงเวลาอ่านค่าเป็นวินาที (default: 1)"
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval ต้องมากกว่า 0")

    addresses = tuple(args.address) if args.address else BH1750_ADDRESSES
    reader = Bh1750Reader(addresses=addresses, bus_number=args.bus, lux_scale=args.lux_scale)
    print("BH1750 continuous reader — กด Ctrl+C เพื่อหยุด")

    try:
        while True:
            started = time.monotonic()
            try:
                lux = reader.read_lux()
                print("\nBH1750")
                print(f"Lux: {lux:.1f}")
            except SensorReadError:
                print("\nBH1750: SENSOR ERROR")
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nหยุดการทดสอบ BH1750")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
