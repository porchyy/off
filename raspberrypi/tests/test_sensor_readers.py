from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from sensor_readers import (
    Bh1750Reader,
    SensorReadError,
    Tof200cReader,
    millimeters_to_centimeters,
)


class FakeBhBus:
    responses: dict[int, object] = {}
    readings: dict[int, object] = {}

    def __init__(self, _bus_number: int) -> None:
        self.closed = False

    def read_byte(self, address: int) -> int:
        response = self.responses[address]
        if isinstance(response, Exception):
            raise response
        return int(response)

    def write_byte(self, _address: int, _value: int) -> None:
        pass

    def read_i2c_block_data(self, address: int, _command: int, _length: int) -> list[int]:
        response = self.readings[address]
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_smbus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "smbus2", SimpleNamespace(SMBus=FakeBhBus))
    FakeBhBus.responses = {}
    FakeBhBus.readings = {}


def test_bh1750_uses_second_supported_address(fake_smbus: None) -> None:
    FakeBhBus.responses = {0x23: OSError("no device"), 0x5C: 1}
    FakeBhBus.readings = {0x5C: [1, 44]}
    reader = Bh1750Reader(measurement_seconds=0)

    assert reader.read_lux() == 250.0
    assert reader.address == 0x5C


def test_bh1750_read_error_clears_cached_address(fake_smbus: None) -> None:
    FakeBhBus.responses = {0x23: 1}
    FakeBhBus.readings = {0x23: OSError("disconnected")}
    reader = Bh1750Reader(addresses=(0x23,), measurement_seconds=0)

    with pytest.raises(SensorReadError):
        reader.read_lux()

    assert reader.address is None


@pytest.mark.parametrize(
    ("millimeters", "centimeters"),
    [(0, 0.0), (624, 62.4), (1234.9, 123.5)],
)
def test_tof200c_converts_millimeters_to_centimeters(
    millimeters: float, centimeters: float
) -> None:
    assert millimeters_to_centimeters(millimeters) == centimeters


def test_tof200c_reports_out_of_range_without_crashing() -> None:
    reader = Tof200cReader()
    reader.sensor_type = "VL53L0X"
    reader._sensor = SimpleNamespace(range=None)

    with pytest.raises(SensorReadError, match="out of range"):
        reader.read_distance_cm()


def test_tof200c_i2c_error_drops_connection_for_retry() -> None:
    class FailingSensor:
        @property
        def range(self) -> int:
            raise OSError("disconnected")

    reader = Tof200cReader()
    reader.sensor_type = "VL53L0X"
    reader._sensor = FailingSensor()

    with pytest.raises(SensorReadError, match="disconnected"):
        reader.read_distance_cm()

    assert reader._sensor is None
