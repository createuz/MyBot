# app/bot/middlewares/request_id_middleware.py
import uuid
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware

from app.core.logger import get_logger


class RequestIDMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        rid = uuid.uuid4().hex
        data["request_id"] = rid
        # data["logger"] = get_logger(rid)
        return await handler(event, data)
