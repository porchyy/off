"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the PostureAI backend."""

    data_dir: Path = Field(default=Path("./database"), alias="POSTUREAI_DATA_DIR")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="POSTUREAI_CORS_ORIGINS",
    )
    host: str = Field(default="0.0.0.0", alias="POSTUREAI_HOST")
    port: int = Field(default=8000, alias="POSTUREAI_PORT")
    admin_token: str = Field(default="", alias="POSTUREAI_ADMIN_TOKEN")
    require_admin_token: bool = Field(default=False, alias="POSTUREAI_REQUIRE_ADMIN_TOKEN")
    retention_days: int = Field(default=30, ge=1, le=365, alias="POSTUREAI_RETENTION_DAYS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "postureai.sqlite"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
