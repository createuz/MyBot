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
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    redis = await get_redis()

    # 1) Try Redis then DB
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    if lang:
        await message.answer(t(lang, "greeting"))
        return

    # 2) ensure user exists with default lang=en and commit immediately
    try:
        user_id = await ensure_user_exists(session=db, chat_id=tg_id, username=username, first_name=first_name,
                                           is_premium=is_premium, default_lang="en")
        await db.commit()
        db.info["committed_by_handler"] = True
        logger.info("start: user ensured id=%s chat_id=%s", user_id, tg_id)
    except Exception as e:
        logger.exception("start: ensure_user failed")
        await message.answer("Server error, try again later.")
        return

    # 3) send language keyboard (non-blocking)
    try:
        await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
    except Exception:
        logger.warning("start: sending welcome failed")
