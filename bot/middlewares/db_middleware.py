# app/bot/middlewares/db_middleware.py
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable
from db.session import db
from core.logger import get_logger

class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        logger = get_logger(request_id)
        async with db.get_session() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                try:
                    await session.commit()
                    logger.info("DB committed (middleware)")
                except Exception as e:
                    await session.rollback()
                    logger.error(f"DB commit failed (middleware): {e}")
                    raise
                return result
            except Exception as exc:
                try:
                    await session.rollback()
                except Exception as e2:
                    logger.error(f"DB rollback failed (middleware): {e2}")
                logger.exception("Exception in handler, rolled back.")
                raise
