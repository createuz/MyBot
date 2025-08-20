# app/core/logger.py
import logging
import sys

import orjson
import structlog
from structlog.typing import FilteringBoundLogger


def orjson_dumps(v, *, default=None):
    return orjson.dumps(v, default=default).decode()


def setup_logger(level: int = logging.INFO) -> FilteringBoundLogger:
    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s")
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(serializer=orjson_dumps),
    ]
    structlog.configure(processors=processors,
                        wrapper_class=structlog.make_filtering_bound_logger(level),
                        logger_factory=structlog.PrintLoggerFactory())
    # reduce SQLAlchemy noise by default
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    return structlog.get_logger()


def get_logger(request_id: str | None = None):
    l = structlog.get_logger()
    return l.bind(rid=request_id) if request_id else l
