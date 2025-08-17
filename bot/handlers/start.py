# app/bot/handlers/start.py
from aiogram import Router, types
from aiogram.filters.command import Command

from bot.handlers.user_service import redis_get_lang, get_lang_cache_then_db, ensure_user_exists
from bot.keyboards import language_keyboard
from bot.translations import t
from core.logger import get_logger
from utils.redis_client import get_redis

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message, **data):
    db = data.get("db")           # session created by middleware only if code uses it
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    redis = await get_redis()

    # 1) Redis-only check first; if found => fast response (no DB used)
    lang = await redis_get_lang(redis, tg_id)
    if lang:
        logger.debug(f"start_handler: redis hit for {tg_id} -> {lang}")
        await message.answer(t(lang, "greeting"))
        return

    # 2) Redis miss -> check DB (this uses session)
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    if lang:
        logger.debug(f"start_handler: db hit for {tg_id} -> {lang}")
        await message.answer(t(lang, "greeting"))
        return

    # 3) Not found anywhere -> create user with default 'en' and ask for language
    try:
        await ensure_user_exists(session=db, chat_id=tg_id, username=username, first_name=first_name,
                                 is_premium=is_premium, default_lang="en")
        # Middleware will commit automatically if changes exist
        logger.info(f"start_handler: ensured user exists (default en) for {tg_id}")
    except Exception as e:
        logger.exception(f"start_handler: failed ensure_user_exists for {tg_id}: {e}")
        await message.answer("Server error, please try again later.")
        return

    # Ask language (do NOT write to Redis yet)
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
