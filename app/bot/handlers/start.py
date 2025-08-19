# app/bot/handlers/start.py
from aiogram import Router, types
from aiogram.filters.command import Command

from app.bot.handlers.user_service import get_lang_cache_then_db, ensure_user_exists
from app.bot.keyboards import language_keyboard
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_client import get_redis

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, **data):
    db = data.get("db")  # LazySessionProxy
    request_id = data.get("request_id")
    logger = get_logger(request_id)

    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    redis = await get_redis()

    # Redis-first quick path + DB fallback
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    if lang:
        await message.answer(t(lang, "greeting"))
        return

    # Not found anywhere -> create minimal user with default 'en'
    try:
        user_id = await ensure_user_exists(session=db, chat_id=tg_id,
                                           username=username, first_name=first_name,
                                           is_premium=is_premium, default_lang="en")
    except Exception:
        logger.exception("start_handler: ensure_user_exists failed for %s", tg_id)
        await message.answer("Server error, try again later.")
        return

    # Commit immediately so DB persists even if message sending fails
    try:
        await db.commit()
        db.info["committed_by_handler"] = True
        logger.info("start_handler: committed new/ensured user id=%s chat_id=%s", user_id, tg_id)
    except Exception:
        logger.exception("start_handler: db commit failed for %s", tg_id)
        await message.answer("Server error, try again later.")
        return

    # Ask language (non-blocking: failure to send won't rollback DB)
    try:
        await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
    except Exception as e:
        logger.warning("start_handler: failed to send welcome to %s: %s", tg_id, e)
