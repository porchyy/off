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
    secret_key: str = Field(
        default="postureai-sso-secret-key-change-in-production",
        alias="POSTUREAI_SECRET_KEY",
    )

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
