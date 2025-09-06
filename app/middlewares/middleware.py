# app/middlewares/logging.py
import time
import traceback
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update, Message, CallbackQuery, InlineQuery, ChatMemberUpdated
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
        request_id = data.get("request_id")
        log = self.logger.bind(rid=request_id) if request_id else self.logger

        update_id = getattr(event, "update_id", None)
        chat_id = None
        try:
            if isinstance(event, Update):
                if event.message and isinstance(event.message, Message):
                    chat_id = event.message.chat.id
                elif event.callback_query and isinstance(event.callback_query, CallbackQuery):
                    chat_id = event.callback_query.message.chat.id if event.callback_query.message else event.callback_query.from_user.id
                elif event.inline_query and isinstance(event.inline_query, InlineQuery):
                    chat_id = event.inline_query.from_user.id
                elif event.my_chat_member and isinstance(event.my_chat_member, ChatMemberUpdated):
                    chat_id = event.my_chat_member.chat.id
                elif event.chat_member and isinstance(event.chat_member, ChatMemberUpdated):
                    chat_id = event.chat_member.chat.id
        except Exception:
            log.warning("chat_id_extract_failed", update_id=update_id, exc_info=True)
            chat_id = None

        try:
            result = await handler(event, data)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000)
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
            raise
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
