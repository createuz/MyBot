# app/core/config.py
from __future__ import annotations

from typing import Optional, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # Bot & run
    bot_token: str = Field(..., env="BOT_TOKEN")
    run_mode: str = Field("polling", env="RUN_MODE")  # "polling" or "webhook"
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Database (prefer full URL or components fallback)
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    db_host: Optional[str] = Field(None, env="DB_HOST")
    db_port: Optional[int] = Field(5432, env="DB_PORT")
    db_user: Optional[str] = Field(None, env="DB_USER")
    db_password: Optional[str] = Field(None, env="DB_PASSWORD")
    db_name: Optional[str] = Field(None, env="DB_NAME")

    # Pooling / PgBouncer
    db_pool_min: int = Field(5, env="DB_POOL_MIN")
    db_pool_max: int = Field(20, env="DB_POOL_MAX")
    use_pgbouncer: bool = Field(False, env="USE_PGBOUNCER")

    # Redis
    redis_url: Optional[str] = Field(..., env="REDIS_URL")

    # Webhook
    webhook_enabled: bool = Field(False, env="WEBHOOK_ENABLED")
    webhook_url: Optional[str] = Field(None, env="WEBHOOK_URL")
    webhook_secret: Optional[str] = Field(None, env="WEBHOOK_SECRET")
    webhook_host: Optional[str] = Field(None, env="WEBHOOK_HOST")
    webhook_port: int = Field(8443, env="WEBHOOK_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    # ---- validators / normalizers ----

    @field_validator("use_pgbouncer", "webhook_enabled", mode="before")
    def _coerce_bool(cls, v: Any) -> bool:
        # Accept "1", "true", "yes", etc.
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)

    @field_validator("redis_url", mode="before")
    def _normalize_redis_url(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, str) and not v.startswith(("redis://", "rediss://")):
            return f"redis://{v}"
        return v

    @model_validator(mode="before")
    def _assemble_database_url(cls, values: dict) -> dict:
        # If DATABASE_URL provided, keep it. Otherwise, try to build from components.
        if values.get("database_url"):
            return values

        host = values.get("db_host")
        user = values.get("db_user")
        password = values.get("db_password")
        name = values.get("db_name")
        port = values.get("db_port") or 5432

        if host and user and password and name:
            driver = "postgresql+asyncpg"
            url = URL.create(
                drivername=driver,
                username=user,
                password=password,
                host=host,
                port=port,
                database=name,
            ).render_as_string(hide_password=False)
            values["database_url"] = url
        return values

    # Convenience read-only property for code clarity
    @property
    def sqlalchemy_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL not configured")
        return self.database_url


# singleton config object (import as: from app.core.config import conf)
conf = Settings()
# print(conf.bot_token)
