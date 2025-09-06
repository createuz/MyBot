# app/middlewares/middleware.py
import time
import traceback
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import (
    TelegramObject,
    Update,
    Message,
    CallbackQuery,
    InlineQuery,
    ChatMemberUpdated,
)
from structlog.typing import FilteringBoundLogger


class ChatLoggerMiddleware(BaseMiddleware):
    def __init__(self, logger: FilteringBoundLogger) -> None:
        super().__init__()
        self.logger = logger

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        start = time.perf_counter()
        bot: Optional[Bot] = data.get("bot")
        request_id = data.get("request_id")  # agar RequestID middleware mavjud bo'lsa

        # bind logger with request id for this update
        log = self.logger.bind(rid=request_id) if request_id else self.logger

        # Extract update_id & chat_id in robust way
        update_id = getattr(event, "update_id", None)
        chat_id = None
        try:
            if isinstance(event, Update):
                if event.message and isinstance(event.message, Message):
                    chat_id = event.message.chat.id
                elif event.callback_query and isinstance(event.callback_query, CallbackQuery):
                    # callback message may be None (inline message)
                    chat_id = event.callback_query.message.chat.id if event.callback_query.message else None
                elif event.inline_query and isinstance(event.inline_query, InlineQuery):
                    chat_id = event.inline_query.from_user.id
                elif event.my_chat_member and isinstance(event.my_chat_member, ChatMemberUpdated):
                    chat_id = event.my_chat_member.chat.id
                elif event.chat_member and isinstance(event.chat_member, ChatMemberUpdated):
                    chat_id = event.chat_member.chat.id
        except Exception:
            # paranoid: ensure middleware never crashes on parsing
            log.warning("chat_id_extract_failed", update_id=update_id, exc_info=True)
            chat_id = None

        try:
            result = await handler(event, data)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000)
            # Log exception with traceback (string) and minimal metadata
            tb = traceback.format_exc()
            log.error(
                "update_handler_exception",
                update_id=update_id,
                chat_id=chat_id,
                bot_id=getattr(bot, "id", None),
                duration_ms=duration_ms,
                exc=str(exc),
                traceback=tb,
            )
            raise  # re-raise so aiogram error middleware can also act if configured
        else:
            duration_ms = round((time.perf_counter() - start) * 1000)
            log.info(
                "update_handled",
                update_id=update_id,
                chat_id=chat_id,
                bot_id=getattr(bot, "id", None),
                duration_ms=duration_ms,
            )
            return result
