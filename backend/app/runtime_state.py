"""Small in-memory status for the single Raspberry Pi sensor client."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class ClientRuntimeState:
    def __init__(self) -> None:
        self.online = False
        self.last_sync_at: str | None = None
        self.message: str | None = None
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def update(self, online: bool, last_sync_at: str | None, message: str | None) -> None:
        self.online = online
        self.last_sync_at = last_sync_at
        self.message = message
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def is_online(self) -> bool:
        """A client that stops heartbeating should not remain green forever."""
        if not self.online:
            return False
        try:
            updated = datetime.fromisoformat(self.updated_at)
        except ValueError:
            return False
        return datetime.now(timezone.utc) - updated <= timedelta(seconds=90)


client_runtime_state = ClientRuntimeState()
