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
