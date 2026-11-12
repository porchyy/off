"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Ergo Agent backend."""

    data_dir: Path = Field(
        default=Path("./database"),
        validation_alias=AliasChoices("ERGO_AGENT_DATA_DIR", "POSTUREAI_DATA_DIR"),
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        validation_alias=AliasChoices("ERGO_AGENT_CORS_ORIGINS", "POSTUREAI_CORS_ORIGINS"),
    )
    host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("ERGO_AGENT_HOST", "POSTUREAI_HOST"),
    )
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("ERGO_AGENT_PORT", "POSTUREAI_PORT"),
    )
    admin_token: str = Field(
        default="",
        validation_alias=AliasChoices("ERGO_AGENT_ADMIN_TOKEN", "POSTUREAI_ADMIN_TOKEN"),
    )
    require_admin_token: bool = Field(
        default=False,
        validation_alias=AliasChoices("ERGO_AGENT_REQUIRE_ADMIN_TOKEN", "POSTUREAI_REQUIRE_ADMIN_TOKEN"),
    )
    retention_days: int = Field(
        default=35,
        ge=1,
        le=365,
        validation_alias=AliasChoices("ERGO_AGENT_RETENTION_DAYS", "POSTUREAI_RETENTION_DAYS"),
    )
    summary_retention_days: int = Field(
        default=365,
        ge=30,
        le=3650,
        validation_alias=AliasChoices("ERGO_AGENT_SUMMARY_RETENTION_DAYS", "POSTUREAI_SUMMARY_RETENTION_DAYS"),
    )
    report_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("ERGO_AGENT_REPORT_DIR", "POSTUREAI_REPORT_DIR"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlite_path(self) -> Path:
        primary = self.data_dir / "ergoagent.sqlite"
        if primary.exists():
            return primary
        legacy = self.data_dir / "postureai.sqlite"
        if legacy.exists():
            return legacy
        return primary

    @property
    def daily_report_dir(self) -> Path:
        return self.report_dir or self.data_dir / "reports"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
