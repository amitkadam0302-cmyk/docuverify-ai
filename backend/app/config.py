from functools import lru_cache
from pathlib import Path
from typing import Annotated, List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            REPOSITORY_ROOT / ".env",
            BACKEND_ROOT / ".env",
            REPOSITORY_ROOT / ".env.production",
            BACKEND_ROOT / ".env.production",
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "DocuVerify AI"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:5173"
    frontend_origin: str = "http://localhost:5173"
    allowed_origins: Annotated[List[str], NoDecode] = Field(default_factory=list)

    database_url: str = (
        "postgresql+psycopg2://docuverify:docuverify@localhost:5432/docuverify_ai"
    )

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    storage_provider: str = "local"
    upload_dir: str = "uploads"
    storage_cache_dir: str = "storage_cache"
    report_dir: str = "reports"
    processed_dir: str = "processed"
    generated_qr_dir: str = "generated_qr"
    public_base_url: str = "http://localhost:8000"
    max_upload_size_mb: int = 10
    auth_rate_limit_per_minute: int = 10
    upload_rate_limit_per_minute: int = 20
    log_level: str = "INFO"
    contact_email: str = "support@docuverify.ai"
    sentry_dsn: str | None = None

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_bucket: str | None = None

    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def secret_key(self) -> str:
        return self.jwt_secret

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def include_frontend_url(self):
        default_dev_origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        }
        if not self.allowed_origins and self.environment.lower() != "production":
            self.allowed_origins.extend(sorted(default_dev_origins))
        for origin in {self.frontend_url, self.frontend_origin}:
            if origin and origin not in self.allowed_origins:
                self.allowed_origins.append(origin)
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must be configured in the environment.")
        if self.environment.lower() == "production" and len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production.")
        self.storage_provider = self.storage_provider.lower()
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
