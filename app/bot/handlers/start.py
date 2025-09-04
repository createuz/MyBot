# app/bot/handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import language_keyboard
from app.bot.states import LanguageSelection
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_manager import RedisManager
from app.utils.user_service import get_lang_cache_then_db, ensure_user_exists

router = Router()


@router.message(CommandStart(), StateFilter('*'))
async def start_handler(message: Message, state: FSMContext, **data):
    db = data.get("db")
    rid = data.get("request_id")
    logger = get_logger(rid)
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)
    await state.clear()
    redis = RedisManager.client()
    lang = await get_lang_cache_then_db(session=db, redis_client=redis, chat_id=tg_id)
    if lang:
        return await message.answer(t(lang, "greeting"))
    try:
        user_id = await ensure_user_exists(
            session=db,
            chat_id=tg_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            default_lang=None
        )
        if getattr(db, "session_created", False):
            db.info["committed_by_handler"] = True
            await db.commit()
        logger.info("start: ensured user id=%s chat_id=%s", user_id, tg_id)
    except Exception:
        logger.exception("start: ensure_user failed")
        try:
            if getattr(db, "session_created", False):
                await db.rollback()
        except Exception:
            logger.exception("start: rollback failed")
        return await message.answer("Server error, try again later.")
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
    return await state.set_state(LanguageSelection.select_language)
