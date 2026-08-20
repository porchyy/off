#!/usr/bin/env python3
"""Blink the LED wired to physical pin 13 (BCM GPIO27) on a Raspberry Pi 5.

Run this with sudo and stop postureai-client first so nothing else owns GPIO17:

    sudo systemctl stop postureai-client
    sudo .venv/bin/python blink_led_pin13.py --times 5
    sudo systemctl start postureai-client
"""

from __future__ import annotations

import argparse
import sys
import time


DEFAULT_CHIP = 15
PHYSICAL_PIN_13_BCM = 27


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blink physical pin 13 / BCM GPIO27 using lgpio")
    parser.add_argument("--chip", type=int, default=DEFAULT_CHIP, help="gpiochip number (default: 15)")
    parser.add_argument("--pin", type=int, default=PHYSICAL_PIN_13_BCM, help="BCM GPIO line (default: 27 / physical pin 13)")
    parser.add_argument("--times", type=int, default=5, help="number of flashes (default: 5)")
    parser.add_argument("--on-seconds", type=float, default=0.5, help="HIGH duration per flash (default: 0.5)")
    parser.add_argument("--off-seconds", type=float, default=0.5, help="LOW duration per flash (default: 0.5)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.chip < 0 or not 0 <= args.pin <= 27:
        print("chip must be non-negative and pin must be a BCM GPIO from 0 to 27", file=sys.stderr)
        return 2

    try:
        import lgpio  # type: ignore
    except ImportError:
        print("lgpio is unavailable; install python3-lgpio or run the Pi setup script", file=sys.stderr)
        return 1

    handle = lgpio.gpiochip_open(args.chip)
    if handle < 0:
        print(f"cannot open /dev/gpiochip{args.chip} (lgpio error {handle})", file=sys.stderr)
        return 1

    try:
        claim_status = lgpio.gpio_claim_output(handle, args.pin, 0)
        if isinstance(claim_status, int) and claim_status < 0:
            print(f"cannot claim BCM GPIO{args.pin} (lgpio error {claim_status})", file=sys.stderr)
            return 1
        flashes = max(1, args.times)
        on_seconds = max(0.0, args.on_seconds)
        off_seconds = max(0.0, args.off_seconds)
        print(f"Blinking physical pin 13 / BCM GPIO{args.pin}: HIGH then LOW, {flashes} times")
        for _ in range(flashes):
            lgpio.gpio_write(handle, args.pin, 1)  # HIGH
            time.sleep(on_seconds)
            lgpio.gpio_write(handle, args.pin, 0)  # LOW
            time.sleep(off_seconds)
        return 0
    finally:
        try:
            lgpio.gpio_write(handle, args.pin, 0)  # always finish LOW
            lgpio.gpio_free(handle, args.pin)
        finally:
            lgpio.gpiochip_close(handle)


if __name__ == "__main__":
    raise SystemExit(main())
