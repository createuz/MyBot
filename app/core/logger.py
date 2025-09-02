# app/core/logger.py
import logging
import sys
from typing import Optional

import orjson
import structlog

from app.core.config import conf


def orjson_dumps(v, *, default=None):
    return orjson.dumps(v, default=default).decode()


def setup_logger():
    level = getattr(logging, conf.bot.log_level.upper(), logging.INFO)
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    processors = [
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
        # structlog.processors.JSONRenderer(serializer=orjson_dumps),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
    )
    return structlog.get_logger()


_logger = setup_logger()


def get_logger(request_id: Optional[str] = None):
    if request_id:
        return _logger.bind(rid=request_id)
    return _logger
