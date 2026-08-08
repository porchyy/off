"""I2C readers for the standalone OfficeGuardian sensor checks."""

from __future__ import annotations

import argparse
import time
from numbers import Real
from typing import Any


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
    ) -> None:
        self.addresses = addresses
        self.bus_number = bus_number
        self.measurement_seconds = measurement_seconds
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
                data = bus.read_i2c_block_data(
                    self.address, BH1750_CONTINUOUS_HIGH_RES, 2
                )
            finally:
                bus.close()

            if len(data) != 2:
                raise OSError("BH1750 returned an incomplete reading")
            raw_value = (data[0] << 8) | data[1]
            return round(raw_value / 1.2, 1)
        except (OSError, FileNotFoundError, TypeError, ValueError) as error:
            self.address = None
            raise SensorReadError(str(error) or "I2C read failed") from error


class SMBusI2C:
    """I2C adapter for CircuitPython VL53 drivers using /dev/i2c-1 directly."""

    def __init__(self, register_address_bytes: int, bus_number: int = I2C_BUS) -> None:
        import smbus2  # type: ignore

        self._smbus2 = smbus2
        self._bus = smbus2.SMBus(bus_number)
        self._register_address_bytes = register_address_bytes
        self._pending_register: tuple[int, bytes] | None = None

    def try_lock(self) -> bool:
        return True

    def unlock(self) -> None:
        pass

    def writeto(
        self,
        address: int,
        buffer: bytes | bytearray,
        *,
        start: int = 0,
        end: int | None = None,
        stop: bool = True,
    ) -> None:
        del stop
        payload = bytes(buffer[start:end])
        if not payload:
            self._bus.write_quick(address)
            return
        if len(payload) == self._register_address_bytes:
            self._pending_register = (address, payload)
            return
        self._bus.i2c_rdwr(self._smbus2.i2c_msg.write(address, payload))

    def readfrom_into(
        self,
        address: int,
        buffer: bytearray,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        length = len(buffer[start:end])
        read_message = self._smbus2.i2c_msg.read(address, length)
        if self._pending_register is not None:
            pending_address, register = self._pending_register
            self._pending_register = None
            if pending_address != address:
                raise OSError("I2C register read address does not match")
            write_message = self._smbus2.i2c_msg.write(address, register)
            self._bus.i2c_rdwr(write_message, read_message)
        else:
            self._bus.i2c_rdwr(read_message)
        buffer[start : start + length] = bytes(read_message)

    def deinit(self) -> None:
        self._bus.close()


def _tof_device_responds(address: int, bus_number: int) -> bool:
    import smbus2  # type: ignore

    bus = smbus2.SMBus(bus_number)
    try:
        bus.write_quick(address)
        return True
    except OSError:
        return False
    finally:
        bus.close()


def _read_register(address: int, register: bytes, length: int, bus_number: int) -> bytes:
    import smbus2  # type: ignore

    bus = smbus2.SMBus(bus_number)
    try:
        write_message = smbus2.i2c_msg.write(address, register)
        read_message = smbus2.i2c_msg.read(address, length)
        bus.i2c_rdwr(write_message, read_message)
        return bytes(read_message)
    finally:
        bus.close()


def detect_tof_sensor(address: int, bus_number: int = I2C_BUS) -> str:
    """Identify the TOF200C controller as VL53L0X or VL53L1X."""
    l1_model_id = _read_register(address, b"\x01\x0f", 1, bus_number)[0]
    if l1_model_id == 0xEA:
        return "VL53L1X"

    l0_identity = _read_register(address, b"\xc0", 3, bus_number)
    if l0_identity == b"\xee\xaa\x10":
        return "VL53L0X"

    raise SensorReadError(
        "ไม่พบ ID ของ VL53L0X หรือ VL53L1X "
        f"(L1X model=0x{l1_model_id:02X}, L0X ID={l0_identity.hex(' ')})"
    )


def millimeters_to_centimeters(value: Real | None) -> float:
    """Convert a valid millimeter reading to centimeters."""
    if value is None or not isinstance(value, Real) or value < 0:
        raise SensorReadError("out of range")
    return round(float(value) / 10, 1)


class Tof200cReader:
    """Read TOF200C distance in centimeters and reconnect after failures."""

    def __init__(self, *, address: int = 0x29, bus_number: int = I2C_BUS) -> None:
        self.address = address
        self.bus_number = bus_number
        self.sensor_type: str | None = None
        self._sensor: Any | None = None
        self._adapter: SMBusI2C | None = None

    def close(self) -> None:
        sensor, adapter, sensor_type = self._sensor, self._adapter, self.sensor_type
        self._sensor = None
        self._adapter = None
        self.sensor_type = None
        if sensor_type == "VL53L1X" and sensor is not None:
            try:
                sensor.stop_ranging()
            except (OSError, RuntimeError, ValueError):
                pass
        if adapter is not None:
            try:
                adapter.deinit()
            except OSError:
                pass

    def connect(self) -> None:
        """Probe, identify, and initialize the connected TOF200C."""
        if self._sensor is not None:
            return
        try:
            if not _tof_device_responds(self.address, self.bus_number):
                raise SensorReadError(f"ไม่พบ TOF200C ที่ 0x{self.address:02X}")
            sensor_type = detect_tof_sensor(self.address, self.bus_number)
            if sensor_type == "VL53L1X":
                import adafruit_vl53l1x  # type: ignore

                adapter = SMBusI2C(register_address_bytes=2, bus_number=self.bus_number)
                sensor = adafruit_vl53l1x.VL53L1X(adapter, address=self.address)
                sensor.start_ranging()
            else:
                import adafruit_vl53l0x  # type: ignore

                adapter = SMBusI2C(register_address_bytes=1, bus_number=self.bus_number)
                sensor = adafruit_vl53l0x.VL53L0X(
                    adapter, address=self.address, io_timeout_s=2
                )
        except ImportError as error:
            self.close()
            raise SensorReadError(f"ไม่พบ dependency: {error.name or 'sensor driver'}") from error
        except (OSError, RuntimeError, ValueError, FileNotFoundError) as error:
            self.close()
            if isinstance(error, SensorReadError):
                raise
            raise SensorReadError(str(error) or "TOF200C initialization failed") from error

        self.sensor_type = sensor_type
        self._adapter = adapter
        self._sensor = sensor

    def read_distance_cm(self) -> float:
        """Return the latest distance in centimeters."""
        try:
            self.connect()
            if self.sensor_type == "VL53L1X":
                deadline = time.monotonic() + 1.0
                while not self._sensor.data_ready:
                    if time.monotonic() >= deadline:
                        raise SensorReadError("measurement timed out")
                    time.sleep(0.01)
                distance_cm = self._sensor.distance
                self._sensor.clear_interrupt()
                if distance_cm is None:
                    raise SensorReadError("out of range")
                return round(float(distance_cm), 1)

            return millimeters_to_centimeters(self._sensor.range)
        except SensorReadError:
            self.close()
            raise
        except (OSError, RuntimeError, ValueError, FileNotFoundError) as error:
            self.close()
            raise SensorReadError(str(error) or "I2C read failed") from error
