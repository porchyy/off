#!/usr/bin/env python3
"""Continuously print BH1750 and TOF200C readings together."""

from __future__ import annotations

import argparse
import time

from sensor_readers import (
    BH1750_ADDRESSES,
    Bh1750Reader,
    SensorReadError,
    Tof200cReader,
    parse_i2c_address,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ทดสอบ BH1750 และ TOF200C พร้อมกัน")
    parser.add_argument(
        "--bh1750-address",
        type=parse_i2c_address,
        action="append",
        help="I2C address ของ BH1750 (ระบุซ้ำได้; default: 0x23, 0x5C)",
    )
    parser.add_argument(
        "--tof200c-address",
        type=parse_i2c_address,
        default=0x29,
        help="I2C address ของ TOF200C (default: 0x29)",
    )
    parser.add_argument("--bus", type=int, default=1, help="I2C bus (default: 1)")
    parser.add_argument(
        "--interval", type=float, default=1.0, help="ช่วงเวลาอ่านค่าเป็นวินาที (default: 1)"
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval ต้องมากกว่า 0")

    bh_addresses = tuple(args.bh1750_address) if args.bh1750_address else BH1750_ADDRESSES
    bh1750 = Bh1750Reader(addresses=bh_addresses, bus_number=args.bus)
    tof200c = Tof200cReader(address=args.tof200c_address, bus_number=args.bus)

    print("--------------------------------")
    print("OfficeGuardian AI Sensors")
    print("--------------------------------")

    try:
        while True:
            started = time.monotonic()
            print(f"\n[{time.strftime('%H:%M:%S')}]")
            healthy = True
            try:
                print(f"Lux: {bh1750.read_lux():.1f}")
            except SensorReadError:
                healthy = False
                print("Lux: SENSOR ERROR")
            try:
                print(f"Distance: {tof200c.read_distance_cm():.1f} cm")
            except SensorReadError:
                healthy = False
                print("Distance: SENSOR ERROR")
            print(f"Status: {'OK' if healthy else 'SENSOR ERROR'}")
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nหยุดการทดสอบเซนเซอร์")
    finally:
        tof200c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
