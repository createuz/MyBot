# app/core/logger.py
import logging
import sys
from typing import Optional

import orjson
import structlog

from app.core.config import conf  # sizning conf obyekt

def orjson_dumps(v, *, default=None):
    return orjson.dumps(v, default=default).decode()

def setup_logger():
    # Get desired level from config (string like "INFO")
    level_name = (getattr(conf, "bot", None) and getattr(conf.bot, "log_level", None)) or "INFO"
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Ensure root has single stdout handler (no duplicate prints)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(level)

    # Minimal fast processors: timestamp + level + JSON render
    processors = [
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(serializer=orjson_dumps),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Reduce aiogram / aiohttp noisy logs: keep WARNING+ERROR only
    for name in ("aiogram", "aiogram.dispatcher", "aiogram.client", "aiohttp", "asyncio"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        lg.propagate = True

    return structlog.get_logger()

_logger = setup_logger()

def get_logger(request_id: Optional[str] = None):
    return _logger.bind(rid=request_id) if request_id else _logger
