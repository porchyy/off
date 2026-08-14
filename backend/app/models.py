"""SQLAlchemy ORM models — mirror the original SQLite schema."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    neck: Mapped[float | None] = mapped_column(Float, nullable=True)
    shoulders: Mapped[float | None] = mapped_column(Float, nullable=True)
    torso: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class MinuteSummary(Base):
    """One compact posture aggregate per UTC minute, produced from Pi samples."""

    __tablename__ = "minute_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    minute_start: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    score_sum: Mapped[float] = mapped_column(Float, nullable=False)
    score_min: Mapped[float] = mapped_column(Float, nullable=False)
    score_max: Mapped[float] = mapped_column(Float, nullable=False)
    neck_sum: Mapped[float] = mapped_column(Float, nullable=False)
    shoulders_sum: Mapped[float] = mapped_column(Float, nullable=False)
    torso_sum: Mapped[float] = mapped_column(Float, nullable=False)
    measurements: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_measurements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DailySummary(Base):
    """Long-lived Bangkok-calendar aggregate retained after minute data expires."""

    __tablename__ = "daily_summaries"

    day: Mapped[str] = mapped_column(String, primary_key=True)
    score_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    periods: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

