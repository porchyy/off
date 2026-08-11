"""I2C readers for the standalone OfficeGuardian sensor checks."""

from __future__ import annotations

import argparse
import math
import time


I2C_BUS = 1
BH1750_ADDRESSES = (0x23, 0x5C)
BH1750_POWER_ON = 0x01
BH1750_CONTINUOUS_HIGH_RES = 0x10


class SensorReadError(RuntimeError):
    """A recoverable sensor or I2C communication error."""


def parse_i2c_address(value: str) -> int:
    """Parse an I2C address such as 0x29 or 41."""
    try:
        address = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("I2C address ต้องเป็นเลข เช่น 0x29") from error
    if not 0x03 <= address <= 0x77:
        raise argparse.ArgumentTypeError("I2C address ต้องอยู่ระหว่าง 0x03 และ 0x77")
    return address


class Bh1750Reader:
    """Read BH1750 brightness values in lux and reconnect after I2C failures."""

    def __init__(
        self,
        *,
        addresses: tuple[int, ...] = BH1750_ADDRESSES,
        bus_number: int = I2C_BUS,
        measurement_seconds: float = 0.18,
        lux_scale: float = 1.0,
    ) -> None:
        self.addresses = addresses
        self.bus_number = bus_number
        self.measurement_seconds = measurement_seconds
        if not math.isfinite(lux_scale) or lux_scale <= 0:
            raise ValueError("lux_scale must be a positive finite number")
        self.lux_scale = lux_scale
        self.address: int | None = None

    def discover(self) -> int:
        """Find a responding BH1750 at either supported address."""
        try:
            import smbus2  # type: ignore
        except ImportError as error:
            raise SensorReadError("ไม่พบ package smbus2") from error

        for address in self.addresses:
            bus = None
            try:
                bus = smbus2.SMBus(self.bus_number)
                bus.read_byte(address)
                self.address = address
                return address
            except (OSError, FileNotFoundError):
                continue
            finally:
                if bus is not None:
                    bus.close()

        self.address = None
        raise SensorReadError("ไม่พบ BH1750 บน I2C bus")

    def read_lux(self) -> float:
        """Return the newest brightness reading in lux."""
        try:
            import smbus2  # type: ignore
        except ImportError as error:
            raise SensorReadError("ไม่พบ package smbus2") from error

        try:
            if self.address is None:
                self.discover()

            bus = smbus2.SMBus(self.bus_number)
            try:
                bus.write_byte(self.address, BH1750_POWER_ON)
                time.sleep(0.01)
                bus.write_byte(self.address, BH1750_CONTINUOUS_HIGH_RES)
                time.sleep(self.measurement_seconds)
                # BH1750 has no register pointer.  SMBus block reads write a
                # command byte immediately before receiving data, which can
                # restart a conversion and make some modules return the same
                # previous sample forever.  Receive the two measurement bytes
                # directly instead.
                read_message = smbus2.i2c_msg.read(self.address, 2)
                bus.i2c_rdwr(read_message)
                data = list(read_message)
            finally:
                bus.close()

            if len(data) != 2:
                raise OSError("BH1750 returned an incomplete reading")
            raw_value = (data[0] << 8) | data[1]
            return round(raw_value / 1.2 * self.lux_scale, 1)
        except (OSError, FileNotFoundError, TypeError, ValueError) as error:
            self.address = None
            raise SensorReadError(str(error) or "I2C read failed") from error
