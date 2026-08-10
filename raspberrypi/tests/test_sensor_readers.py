from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from sensor_readers import (
    Bh1750Reader,
    SensorReadError,
)


class FakeBhBus:
    responses: dict[int, object] = {}
    readings: dict[int, object] = {}

    def __init__(self, _bus_number: int) -> None:
        self.closed = False
        self.writes: list[tuple[int, int]] = []

    def read_byte(self, address: int) -> int:
        response = self.responses[address]
        if isinstance(response, Exception):
            raise response
        return int(response)

    def write_byte(self, address: int, value: int) -> None:
        self.writes.append((address, value))

    def i2c_rdwr(self, message) -> None:
        response = self.readings[message.address]
        if isinstance(response, Exception):
            raise response
        message.data = list(response)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_smbus(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReadMessage:
        def __init__(self, address: int, _length: int) -> None:
            self.address = address
            self.data: list[int] = []

        def __iter__(self):
            return iter(self.data)

    monkeypatch.setitem(
        sys.modules,
        "smbus2",
        SimpleNamespace(
            SMBus=FakeBhBus,
            i2c_msg=SimpleNamespace(read=FakeReadMessage),
        ),
    )
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
