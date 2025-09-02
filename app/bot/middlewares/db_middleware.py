# app/bot/middlewares/db_middleware.py
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware

from app.core.logger import get_logger
from app.db.lazy_session import LazySessionProxy
from app.db.session import AsyncSessionLocal

logger = get_logger()


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        rid = data.get("request_id")
        log = logger.bind(rid=rid)
        proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
        data["db"] = proxy
        try:
            result = await handler(event, data)

            if not proxy.session_created:
                log.debug("DB middleware: session not created")
                return result

            session = proxy.get_underlying_session()
            if session.info.get("committed_by_handler"):
                log.debug("DB middleware: handler committed")
                await session.close()
                return result

            try:
                has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(
                    session.in_transaction())
            except Exception:
                has_changes = True

            if has_changes:
                await session.commit()
                log.info("DB middleware: committed")
            else:
                log.debug("DB middleware: nothing to commit")
            await session.close()
            return result
        except Exception:
            if proxy.session_created:
                session = proxy.get_underlying_session()
                if not session.info.get("committed_by_handler"):
                    try:
                        await session.rollback()
                        log.info("DB middleware: rolled back")
                    except Exception:
                        log.exception("rollback failed")
                try:
                    await session.close()
                except Exception:
                    log.exception("close failed")
            log.exception("Exception in handler")
            raise
