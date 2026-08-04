from __future__ import annotations

import asyncio

from app.camera_signaling import CameraSignalingBroker


def test_broker_allows_one_pi_and_one_viewer_only():
    async def check() -> None:
        broker = CameraSignalingBroker()
        pi = object()
        viewer = object()

        assert await broker.register("pi", pi) is True
        assert await broker.register("pi", object()) is False
        assert await broker.register("viewer", viewer) is True
        assert await broker.register("viewer", object()) is False
        assert await broker.peer("pi") is viewer
        assert await broker.peer("viewer") is pi

        await broker.unregister("viewer", viewer)
        assert await broker.peer("pi") is None

    asyncio.run(check())
