"""Pydantic request/response models for PostureAI API & OAuth/Model Sync."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["caution", "risk"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(ApiModel):
    ok: bool
    db_ok: bool = Field(serialization_alias="dbOk")
    db_path: str = Field(serialization_alias="dbPath")
    data_dir: str = Field(serialization_alias="dataDir")
    time: str


class SettingsModel(ApiModel):
    risk_threshold: int = Field(ge=1, le=99, serialization_alias="riskThreshold")
    risk_seconds: int = Field(ge=5, le=600, serialization_alias="riskSeconds")
    data_dir: str = Field(serialization_alias="dataDir")
    sound_enabled: bool = Field(serialization_alias="soundEnabled")
    voice_enabled: bool = Field(default=True, serialization_alias="voiceEnabled")
    desktop_enabled: bool = Field(serialization_alias="desktopEnabled")
    pending_data_dir: str | None = Field(default=None, serialization_alias="pendingDataDir")


class SettingsUpdate(ApiModel):
    risk_threshold: int | None = Field(default=None, ge=1, le=99, alias="riskThreshold")
    risk_seconds: int | None = Field(default=None, ge=5, le=600, alias="riskSeconds")
    data_dir: str | None = Field(default=None, alias="dataDir")
    sound_enabled: bool | None = Field(default=None, alias="soundEnabled")
    voice_enabled: bool | None = Field(default=None, alias="voiceEnabled")
    desktop_enabled: bool | None = Field(default=None, alias="desktopEnabled")


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

