"""Default settings + persistence helpers for the settings key/value table."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .config import settings
from .models import Setting

DEFAULTS: dict[str, Any] = {
    "riskThreshold": 60,
    "riskSeconds": 45,
    "dataDir": str(settings.data_dir.resolve()),
    "soundEnabled": True,
    "desktopEnabled": False,
}


def ensure_defaults(db: Session) -> None:
    """Insert default settings rows that don't already exist."""
    for key, value in DEFAULTS.items():
        exists = db.get(Setting, key)
        if exists is None:
            db.add(Setting(key=key, value=json.dumps(value)))
    db.commit()
    # Always keep dataDir in sync with the resolved data dir at boot.
    db.merge(Setting(key="dataDir", value=json.dumps(str(settings.data_dir.resolve()))))
    db.commit()


def get_all(db: Session) -> dict[str, Any]:
    values = dict(DEFAULTS)
    for row in db.query(Setting).all():
        try:
            values[row.key] = json.loads(row.value)
        except json.JSONDecodeError:
            continue
    values["dataDir"] = str(settings.data_dir.resolve())
    return values
