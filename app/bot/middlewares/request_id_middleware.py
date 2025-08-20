# app/bot/middlewares/request_id.py
import uuid

from aiogram import BaseMiddleware

from app.core.logger import get_logger


class RequestIDMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        rid = uuid.uuid4().hex
        data["request_id"] = rid
        data["logger"] = get_logger(rid)
        return await handler(event, data)
