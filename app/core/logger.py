# app/core/logger.py
import logging
import sys
from typing import Optional


class RequestFormatter(logging.Formatter):
    def format(self, record):
        request_id = getattr(record, "request_id", None)
        if request_id:
            record.msg = f"[rid={request_id}] {record.getMessage()}"
            record.args = ()
        return super().format(record)


logger = logging.getLogger("mybot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
handler.setFormatter(RequestFormatter(fmt))
logger.addHandler(handler)


def get_logger(request_id: Optional[str] = None):
    if request_id:
        return logging.LoggerAdapter(logger, {"request_id": request_id})
    return logger
