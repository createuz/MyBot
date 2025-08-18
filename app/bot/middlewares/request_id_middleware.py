# app/bot/middlewares/request_id_middleware.py
import uuid
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable

class RequestIDMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        rid = uuid.uuid4().hex
        data["request_id"] = rid
        return await handler(event, data)
