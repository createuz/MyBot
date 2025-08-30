# app/core/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name, default)
    return v if v is not None else None


def _getint(name: str, default: Optional[int] = None) -> Optional[int]:
    v = os.getenv(name, None)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default


def _getbool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, None)
    if v is None:
        return default
    vs = str(v).strip().lower()
    return vs in ("1", "true", "yes", "on", "y", "t")


@dataclass
class DatabaseConfig:
    # Accept either DB_URL or components (DB_HOST etc.)
    url: Optional[str] = field(default_factory=lambda: _getenv("DB_URL"))
    host: Optional[str] = field(default_factory=lambda: _getenv("DB_HOST"))
    port: int = field(default_factory=lambda: _getint("DB_PORT", 5432))
    user: Optional[str] = field(default_factory=lambda: _getenv("DB_USER"))
    password: Optional[str] = field(default_factory=lambda: _getenv("DB_PASSWORD"))
    name: Optional[str] = field(default_factory=lambda: _getenv("DB_NAME"))
    driver: str = field(default_factory=lambda: _getenv("DB_DRIVER") or "asyncpg")
    db_system: str = field(default_factory=lambda: _getenv("DB_SYSTEM") or "postgresql")
    pool_min: int = field(default_factory=lambda: _getint("DB_POOL_MIN", 5))
    pool_max: int = field(default_factory=lambda: _getint("DB_POOL_MAX", 20))
    use_pgbouncer: bool = field(default_factory=lambda: _getbool("USE_PGBOUNCER", False))

    def build_db_url(self) -> str:
        if self.url:
            return self.url
        if not (self.host and self.user and self.password and self.name):
            raise RuntimeError("Database not configured: please set DB_URL in .env")
        drivername = f"{self.db_system}+{self.driver}" if self.driver else self.db_system
        return URL.create(
            drivername=drivername,
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        ).render_as_string(hide_password=False)


@dataclass
class RedisConfig:
    url: Optional[str] = field(default_factory=lambda: _getenv("REDIS_URL"))
    host: str = field(default_factory=lambda: _getenv("REDIS_HOST") or "localhost")
    port: int = field(default_factory=lambda: _getint("REDIS_PORT", 6379))
    db: int = field(default_factory=lambda: _getint("REDIS_DB", 0))
    password: Optional[str] = field(default_factory=lambda: _getenv("REDIS_PASSWORD"))
    ttl_state: int = field(default_factory=lambda: _getint("REDIS_TTL_STATE", 3600))
    ttl_data: int = field(default_factory=lambda: _getint("REDIS_TTL_DATA", 7 * 24 * 3600))

    def build_redis_url(self) -> str:
        if self.url:
            return self.url
        if self.password:
            pwd = quote_plus(self.password)
            return f"redis://:{pwd}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class WebhookConfig:
    enabled: bool = field(default_factory=lambda: _getbool("WEBHOOK_ENABLED", False))
    url: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_URL"))
    secret: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_SECRET"))
    host: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_HOST"))
    port: int = field(default_factory=lambda: _getint("WEBHOOK_PORT", 8443))
    max_updates_in_queue: Optional[int] = field(default_factory=lambda: _getint("MAX_UPDATES_IN_QUEUE", None))


@dataclass
class BotConfig:
    token: Optional[str] = field(default_factory=lambda: _getenv("BOT_TOKEN"))
    run_mode: str = field(default_factory=lambda: _getenv("RUN_MODE") or "polling")
    log_level: str = field(default_factory=lambda: _getenv("LOG_LEVEL") or "INFO")
    username: Optional[str] = field(default_factory=lambda: _getenv("BOT_USERNAME"))
    start_user: Optional[str] = field(default_factory=lambda: _getenv("START_USER"))
    start_group: Optional[str] = field(default_factory=lambda: _getenv("START_GROUP"))


@dataclass
class AppConfig:
    bot: BotConfig = field(default_factory=BotConfig)
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    admin_id: Optional[int] = field(default_factory=lambda: _getint("ADMIN", None))

    @property
    def database_url(self) -> str:
        return self.db.build_db_url()

    @property
    def redis_url(self) -> str:
        return self.redis.build_redis_url()


conf: AppConfig = AppConfig()

