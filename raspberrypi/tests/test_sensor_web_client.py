from __future__ import annotations

import requests
from sensor_readers import SensorReadError
from sensor_web_client import publish_sensor_payload, read_sensor_payload


class Reader:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    def read_lux(self):
        if self.error:
            raise self.error
        return self.value

    def read_distance_cm(self):
        if self.error:
            raise self.error
        return self.value


def test_read_sensor_payload_keeps_working_sensor_value() -> None:
    payload = read_sensor_payload(
        Reader(error=SensorReadError("BH1750 disconnected")),
        Reader(value=62.4),
    )

    assert payload == {
        "lux": None,
        "distanceCm": 62.4,
        "bh1750Ok": False,
        "tof200cOk": True,
    }


def test_publish_sensor_payload_uses_latest_endpoint_and_timeout() -> None:
    calls = []

    class Response:
        def __init__(self) -> None:
            self.closed = False

        def raise_for_status(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    response = Response()

    def put(url, *, json, timeout):
        calls.append((url, json, timeout))
        return response

    payload = {
        "lux": 423.5,
        "distanceCm": 62.4,
        "bh1750Ok": True,
        "tof200cOk": True,
    }
    publish_sensor_payload(
        "http://127.0.0.1:8000/api/sensors/latest", payload, 3.0, put
    )

    assert calls == [
        ("http://127.0.0.1:8000/api/sensors/latest", payload, 3.0)
    ]
    assert response.closed is True


def test_publish_sensor_payload_closes_failed_response() -> None:
    class FailedResponse:
        def __init__(self) -> None:
            self.closed = False

        def raise_for_status(self) -> None:
            raise requests.HTTPError("backend unavailable")

        def close(self) -> None:
            self.closed = True

    response = FailedResponse()

    try:
        publish_sensor_payload(
            "http://127.0.0.1:8000/api/sensors/latest",
            {"lux": 100.0, "distanceCm": 50.0, "bh1750Ok": True, "tof200cOk": True},
            3.0,
            lambda *args, **kwargs: response,
        )
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("HTTPError was not raised")

    assert response.closed is True
