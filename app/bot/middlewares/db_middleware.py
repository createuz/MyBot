# app/bot/middlewares/db_middleware.py
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable
from app.db.lazy_session import LazySessionProxy
from app.db.session import AsyncSessionLocal  # async_sessionmaker

from app.core.logger import get_logger

logger = get_logger()

class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        log = logger.bind(rid=request_id)
        proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
        data["db"] = proxy

        try:
            result = await handler(event, data)

            # if session was never created — nothing to commit/close
            if not proxy.session_created:
                log.debug("DBMiddleware: session not created during handler")
                return result

            session = proxy.get_underlying_session()
            # if handler already committed explicitly, skip commit
            if session.info.get("committed_by_handler"):
                log.debug("DBMiddleware: handler already committed")
                await session.close()
                return result

            # commit only if there are changes or active transaction
            try:
                has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(session.in_transaction())
            except Exception:
                has_changes = True

            if has_changes:
                await session.commit()
                log.info("DBMiddleware: committed")
            else:
                log.debug("DBMiddleware: nothing to commit")

            await session.close()
            return result

        except Exception as exc:
            # if session created, rollback
            if proxy.session_created:
                session = proxy.get_underlying_session()
                if not session.info.get("committed_by_handler"):
                    try:
                        await session.rollback()
                        log.info("DBMiddleware: rolled back due to exception")
                    except Exception:
                        log.exception("DBMiddleware rollback failed")
                try:
                    await session.close()
                except Exception:
                    log.exception("Session close failed")
            log.exception("Exception in handler")
            raise
