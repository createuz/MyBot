# # app/bot/middlewares/db_middleware.py
# from typing import Callable, Any, Awaitable
#
# from aiogram import BaseMiddleware
#
# from app.core.logger import get_logger
# from app.db.lazy_session import LazySessionProxy
# from app.db.session import AsyncSessionLocal
#
# logger = get_logger()
#
#
# class DBSessionMiddleware(BaseMiddleware):
#     async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
#         request_id = data.get("request_id")
#         log = get_logger(request_id)
#         proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
#         data["db"] = proxy
#         try:
#             result = await handler(event, data)
#             if not proxy.session_created:
#                 log.debug("DBSessionMiddleware: no session created")
#                 return result
#
#             session = proxy.get_underlying_session()
#             if session.info.get("committed_by_handler"):
#                 log.debug("DBSessionMiddleware: skipping commit, handler already committed")
#                 await session.close()
#                 return result
#
#             # commit only if changes present
#             try:
#                 has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(
#                     session.in_transaction())
#             except Exception:
#                 # if introspection fails, conservatively commit
#                 has_changes = True
#
#             if has_changes:
#                 await session.commit()
#                 log.info("DBSessionMiddleware: committed")
#             else:
#                 log.debug("DBSessionMiddleware: nothing to commit")
#             await session.close()
#             return result
#
#         except Exception:
#             if proxy.session_created:
#                 session = proxy.get_underlying_session()
#                 if not session.info.get("committed_by_handler"):
#                     try:
#                         await session.rollback()
#                         log.info("DBSessionMiddleware: rolled back due to exception")
#                     except Exception:
#                         log.exception("DBSessionMiddleware: rollback failed")
#                 try:
#                     await session.close()
#                 except Exception:
#                     log.exception("DBSessionMiddleware: session close failed")
#             log.exception("DBSessionMiddleware: exception in handler")
#             raise


from typing import Callable, Any, Awaitable

# app/bot/middlewares/db_middleware.py  (yangi / yangilangan)
from aiogram import BaseMiddleware

from app.core.logger import get_logger
from app.db.lazy_session import LazySessionProxy
from app.db.session import AsyncSessionLocal


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        logger = get_logger(request_id)
        proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
        data["db"] = proxy

        try:
            result = await handler(event, data)

            # If session was never created (no DB access) — do nothing.
            if not proxy.session_created:
                logger.debug("DBSessionMiddleware: no session created")
                return result

            session = proxy.get_underlying_session()
            if not session:
                logger.debug("DBSessionMiddleware: session missing -> nothing to do")
                return result

            # If handler committed explicitly -> skip commit
            if session.info.get("committed_by_handler"):
                logger.debug("DBSessionMiddleware: skipping commit, handler already committed")
                await session.close()
                return result

            # Commit only if actual writes happened (or SQLAlchemy tracked new/dirty/deleted)
            writes_flag = bool(session.info.get("writes", False))
            has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted) or writes_flag

            if has_changes:
                await session.commit()
                logger.info("DBSessionMiddleware: committed",
                            reason="writes_flag" if writes_flag else "session_new_dirty_deleted",
                            writes=writes_flag, new=len(session.new), dirty=len(session.dirty),
                            deleted=len(session.deleted))
            else:
                logger.debug("DBSessionMiddleware: nothing to commit (read-only)")

            await session.close()
            return result

        except Exception as exc:
            # rollback only if session was created and handler didn't commit
            if proxy.session_created:
                session = proxy.get_underlying_session()
                if session and not session.info.get("committed_by_handler"):
                    try:
                        await session.rollback()
                        logger.info("DBSessionMiddleware: rolled back due to exception")
                    except Exception:
                        logger.exception("DBSessionMiddleware: rollback failed")
                try:
                    if session:
                        await session.close()
                except Exception:
                    logger.exception("DBSessionMiddleware: session close failed")
            logger.exception("Exception in handler")
            raise
