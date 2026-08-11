"""I2C readers for the standalone OfficeGuardian sensor checks."""

from __future__ import annotations

import argparse
import math
import time


I2C_BUS = 1
BH1750_ADDRESSES = (0x23, 0x5C)
BH1750_POWER_ON = 0x01
BH1750_CONTINUOUS_HIGH_RES = 0x10
VL53L1X_DEFAULT_ADDRESS = 0x29


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


class Vl53l1xReader:
    """Read a VL53L1X / TOF400C distance sensor in centimetres.

    The CircuitPython driver uses the Pi's default I2C bus (SDA pin 3 / SCL
    pin 5).  It is imported only when the sensor is used, keeping BH1750
    operation available if the optional TOF package or hardware is absent.
    """

    def __init__(
        self,
        *,
        address: int = VL53L1X_DEFAULT_ADDRESS,
        distance_mode: int = 1,
        timing_budget: int = 50,
        read_timeout_seconds: float = 0.5,
    ) -> None:
        if distance_mode not in (1, 2):
            raise ValueError("distance_mode must be 1 (short) or 2 (long)")
        if timing_budget not in (15, 20, 33, 50, 100, 200, 500):
            raise ValueError("unsupported VL53L1X timing budget")
        if not math.isfinite(read_timeout_seconds) or read_timeout_seconds <= 0:
            raise ValueError("read_timeout_seconds must be positive")
        self.address = address
        self.distance_mode = distance_mode
        self.timing_budget = timing_budget
        self.read_timeout_seconds = read_timeout_seconds
        self._sensor: object | None = None

    def _connect(self) -> object:
        if self._sensor is not None:
            return self._sensor
        try:
            import adafruit_vl53l1x  # type: ignore
            import board  # type: ignore
        except ImportError as error:
            raise SensorReadError("ไม่พบ package adafruit-circuitpython-vl53l1x") from error
        try:
            sensor = adafruit_vl53l1x.VL53L1X(board.I2C(), address=self.address)
            sensor.distance_mode = self.distance_mode
            sensor.timing_budget = self.timing_budget
            sensor.start_ranging()
            self._sensor = sensor
            return sensor
        except (OSError, RuntimeError, ValueError) as error:
            self._sensor = None
            raise SensorReadError(str(error) or "VL53L1X I2C initialization failed") from error

    def read_distance_cm(self) -> float:
        """Return a fresh TOF distance in centimetres and recover after errors."""
        try:
            sensor = self._connect()
            deadline = time.monotonic() + self.read_timeout_seconds
            while not bool(sensor.data_ready):
                if time.monotonic() >= deadline:
                    raise TimeoutError("VL53L1X measurement timed out")
                time.sleep(0.01)
            distance = sensor.distance
            sensor.clear_interrupt()
            if distance is None or not math.isfinite(float(distance)) or float(distance) < 0:
                raise ValueError("VL53L1X returned an invalid distance")
            return round(float(distance), 1)
        except (OSError, RuntimeError, ValueError, TimeoutError, TypeError) as error:
            self.close()
            raise SensorReadError(str(error) or "VL53L1X read failed") from error

    def close(self) -> None:
        sensor, self._sensor = self._sensor, None
        if sensor is None:
            return
        try:
            sensor.stop_ranging()
        except (OSError, RuntimeError, ValueError):
            pass
