# app/bot/handlers/start.py
from aiogram import Router, types
from aiogram.filters.command import Command

from app.bot.handlers.user_service import redis_get_lang, get_lang_cache_then_db, ensure_user_exists
from app.bot.keyboards import language_keyboard
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_client import get_redis

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, **data):
    """
    1) Redis-first tekshiradi (tez yo'l)
    2) Agar Redis miss bo'lsa DB ga qaraydi (bu paytda lazy session yaratiladi)
    3) Agar DBda ham yo'q bo'lsa -> ensure_user_exists() -> COMMIT (darhol)
    4) Keyin tilni so'rash (keyboard) yuboriladi; bu yuborishda xatolik bo'lsa ham rollback bo'lmaydi
    """
    db = data.get("db")  # LazySessionProxy
    request_id = data.get("request_id")
    logger = get_logger(request_id)

    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    redis = await get_redis()

    # 1) Redis-first quick check (no DB created if hit)
    lang = await redis_get_lang(redis, tg_id)
    if lang:
        logger.debug(f"start: redis hit for {tg_id} -> {lang}")
        await message.answer(t(lang, "greeting"))
        return

    # 2) Redis miss -> check DB (this will create session lazily)
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    if lang:
        logger.debug(f"start: db hit for {tg_id} -> {lang}")
        await message.answer(t(lang, "greeting"))
        return

    # 3) Not found anywhere -> create user WITH default lang 'en'
    try:
        user_id = await ensure_user_exists(session=db,
                                           chat_id=tg_id,
                                           username=username,
                                           first_name=first_name,
                                           is_premium=is_premium,
                                           default_lang="en")
    except Exception as e:
        logger.exception("start: ensure_user_exists failed for %s", tg_id)
        await message.answer("Server error, please try again later.")
        return

    # 4) COMMIT immediately so user is persisted even if notification fails
    try:
        await db.commit()
        # mark session as committed to avoid middleware double-commit
        db.info["committed_by_handler"] = True
        logger.info(f"start: committed new/ensured user id={user_id} chat_id={tg_id}")
    except Exception as e:
        logger.exception("start: commit failed for %s", tg_id)
        await message.answer("Server error, please try again later.")
        return

    # 5) Now send the welcome/ask-language message (wrap in try/except so errors don't rollback DB)
    try:
        await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
    except Exception as e:
        # Log but DO NOT raise — DB already committed
        logger.warning("start: failed to send welcome to %s: %s", tg_id, e)
