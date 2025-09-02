# app/core/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _getenv(k: str, default=None):
    v = os.getenv(k, default)
    return v if v is not None and v != "" else default


def _getint(k: str, default: int):
    v = _getenv(k)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def _getbool(k: str, default: bool):
    v = _getenv(k)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y")


@dataclass
class DBConf:
    url: Optional[str] = field(default_factory=lambda: _getenv("DB_URL") or _getenv("DATABASE_URL"))
    host: Optional[str] = field(default_factory=lambda: _getenv("DB_HOST") or _getenv("PG_HOST"))
    port: int = field(default_factory=lambda: _getint("DB_PORT", 5432))
    user: Optional[str] = field(default_factory=lambda: _getenv("DB_USER") or _getenv("PG_USER"))
    password: Optional[str] = field(default_factory=lambda: _getenv("DB_PASSWORD") or _getenv("PG_PASSWORD"))
    name: Optional[str] = field(default_factory=lambda: _getenv("DB_NAME") or _getenv("PG_NAME"))
    driver: str = field(default_factory=lambda: _getenv("DB_DRIVER") or "asyncpg")
    db_system: str = field(default_factory=lambda: _getenv("DB_SYSTEM") or "postgresql")
    pool_min: int = field(default_factory=lambda: _getint("DB_POOL_MIN", 5))
    pool_max: int = field(default_factory=lambda: _getint("DB_POOL_MAX", 20))
    use_pgbouncer: bool = field(default_factory=lambda: _getbool("USE_PGBOUNCER", False))

    def sqlalchemy_url(self) -> str:
        if self.url:
            return self.url
        if not (self.host and self.user and self.password and self.name):
            raise RuntimeError("Database not configured: set DB_URL or DB_HOST/DB_USER/DB_PASSWORD/DB_NAME")
        drivername = f"{self.db_system}+{self.driver}"
        return URL.create(
            drivername=drivername,
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        ).render_as_string(hide_password=False)


@dataclass
class RedisConf:
    url: Optional[str] = field(default_factory=lambda: _getenv("REDIS_URL"))
    host: str = field(default_factory=lambda: _getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: _getint("REDIS_PORT", 6379))
    db: int = field(default_factory=lambda: _getint("REDIS_DB", 0))
    password: Optional[str] = field(default_factory=lambda: _getenv("REDIS_PASSWORD"))
    ttl_state: int = field(default_factory=lambda: _getint("REDIS_TTL_STATE", 3600))
    ttl_data: int = field(default_factory=lambda: _getint("REDIS_TTL_DATA", 7 * 24 * 3600))

    def url_or_build(self) -> str:
        if self.url:
            return self.url
        if self.password:
            pwd = quote_plus(self.password)
            return f"redis://:{pwd}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class BotConf:
    token: str = field(default_factory=lambda: _getenv("BOT_TOKEN", ""))
    run_mode: str = field(default_factory=lambda: _getenv("RUN_MODE", "polling"))  # polling|webhook|local
    username: Optional[str] = field(default_factory=lambda: _getenv("BOT_USERNAME"))
    log_level: str = field(default_factory=lambda: _getenv("LOG_LEVEL", "INFO"))


@dataclass
class WebhookConf:
    enabled: bool = field(default_factory=lambda: _getbool("WEBHOOK_ENABLED", False))
    url: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_URL"))
    secret: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_SECRET"))
    host: Optional[str] = field(default_factory=lambda: _getenv("WEBHOOK_HOST"))
    port: int = field(default_factory=lambda: _getint("WEBHOOK_PORT", 8443))


@dataclass
class Conf:
    bot: BotConf = field(default_factory=BotConf)
    db: DBConf = field(default_factory=DBConf)
    redis: RedisConf = field(default_factory=RedisConf)
    webhook: WebhookConf = field(default_factory=WebhookConf)
    admin: Optional[int] = field(default_factory=lambda: _getint("ADMIN", None))


conf = Conf()
