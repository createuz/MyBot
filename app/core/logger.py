# # app/core/logger.py
# import logging
# import sys
# from typing import Optional
#
# import orjson
# import structlog
#
# from app.core.config import conf
#
#
# def orjson_dumps(v, *, default=None):
#     return orjson.dumps(v, default=default).decode()
#
#
# def setup_logger():
#     level = getattr(logging, conf.bot.log_level.upper(), logging.INFO)
#     logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
#     processors = [
#         structlog.processors.TimeStamper(fmt="iso", utc=True),
#         structlog.processors.add_log_level,
#         structlog.processors.StackInfoRenderer(),
#         structlog.processors.format_exc_info,
#         structlog.processors.JSONRenderer(),
#         # structlog.processors.JSONRenderer(serializer=orjson_dumps),
#     ]
#     structlog.configure(
#         processors=processors,
#         wrapper_class=structlog.make_filtering_bound_logger(level),
#         logger_factory=structlog.PrintLoggerFactory(),
#     )
#     return structlog.get_logger()
#
#
# _logger = setup_logger()
#
#
# def get_logger(request_id: Optional[str] = None):
#     if request_id:
#         return _logger.bind(rid=request_id)
#     return _logger

# app/core/logger.py
import logging
import sys
from typing import Optional

import orjson
import structlog

from app.core.config import conf  # sizdagi conf bo'lishi kerak


def orjson_dumps(v, *, default=None):
    return orjson.dumps(v, default=default).decode()


def setup_logger():
    level_name = (conf.bot.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Basic logging -> stdout
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(message)s",
    )

    # Minimal processors for speed: timestamp + level + json
    processors = [
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        # include stack info only for errors (we will log exc_info explicitly)
        structlog.processors.JSONRenderer(serializer=orjson_dumps),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    # Aiogram loglarni SUSpress qilish: DEBUG/INFO ni o'chiramiz, WARNING+ERROR qoldiramiz
    for name in ("aiogram", "aiogram.dispatcher", "aiogram.client", "aiogram.fsm"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)  # DEBUG/INFO lar chiqmaydi, WARNING+ERROR qoladi
        lg.propagate = True  # root handlerga o'tsin (structlog orqali render bo'ladi)

    return structlog.get_logger()


_logger = setup_logger()


def get_logger(request_id: Optional[str] = None):
    return _logger.bind(rid=request_id) if request_id else _logger
