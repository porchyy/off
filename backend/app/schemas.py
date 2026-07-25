"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["caution", "risk"]


class HealthResponse(BaseModel):
    ok: bool
    db_ok: bool
    db_path: str
    data_dir: str
    time: str


class SettingsModel(BaseModel):
    risk_threshold: int = Field(ge=1, le=99)
    risk_seconds: int = Field(ge=5, le=600)
    data_dir: str
    sound_enabled: bool
    desktop_enabled: bool
    pending_data_dir: str | None = None


class SettingsUpdate(BaseModel):
    risk_threshold: int | None = Field(default=None, ge=1, le=99)
    risk_seconds: int | None = Field(default=None, ge=5, le=600)
    data_dir: str | None = None
    sound_enabled: bool | None = None
    desktop_enabled: bool | None = None


class SampleIn(BaseModel):
    score: float = Field(ge=0, le=100)
    neck: float
    shoulders: float
    torso: float

    @field_validator("neck", "shoulders", "torso")
    @classmethod
    def _is_finite(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("must be finite")
        return value


class AlertIn(BaseModel):
    severity: Severity
    message: str = Field(max_length=160)


class AlertOut(BaseModel):
    id: int
    severity: str
    message: str
    created_at: str


class SummaryResponse(BaseModel):
    samples: int
    average: int | None
    alerts: list[AlertOut]


class DailyStat(BaseModel):
    label: str
    average: int
    samples: int


class WeeklyAlertStat(BaseModel):
    label: str
    alerts: int


class StatsResponse(BaseModel):
    daily: list[DailyStat]
    weekly_alerts: list[WeeklyAlertStat]


class ExportResponse(BaseModel):
    exported_at: datetime
    db_path: str
    rows: list[dict]


class OkResponse(BaseModel):
    ok: bool = True
