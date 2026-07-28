"""SQLAlchemy ORM models — mirror the original SQLite schema."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String, nullable=False, default="google")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class CustomModelArtifact(Base):
    __tablename__ = "custom_models"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    model_json: Mapped[str] = mapped_column(Text, nullable=False)
    weights_base64: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    neck: Mapped[float | None] = mapped_column(Float, nullable=True)
    shoulders: Mapped[float | None] = mapped_column(Float, nullable=True)
    torso: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
