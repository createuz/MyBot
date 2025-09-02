# app/bot/handlers/start.py
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.filters.command import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.logger import get_logger
from app.utils.user_service import get_lang_cache_then_db, ensure_user_exists
from app.utils.redis_manager import RedisManager
from app.bot.keyboards import language_keyboard
from app.bot.translations import t
from app.utils.states import LanguageSelection  # define FSM states module

router = Router()

@router.message(CommandStart(), StateFilter('*'))
async def start_handler(message: Message, state: FSMContext, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    # clear any existing state
    await state.clear()

    # get redis client
    redis = RedisManager.client()

    # 1) check cache -> db
    lang = await get_lang_cache_then_db(session=db, redis_client=redis, chat_id=tg_id)
    if lang:
        await message.answer(t(lang, "greeting"))
        return

    # 2) not found: ensure user exists in DB with language = None
    try:
        user_id = await ensure_user_exists(session=db, chat_id=tg_id, username=username,
                                           first_name=first_name, is_premium=is_premium,
                                           default_lang=None)
        # we want immediate persistence for new user so middleware will commit automatically
        # set flag so middleware won't double-commit (optional)
        if db.session_created:
            db.info["committed_by_handler"] = False  # do not signal commit yet; middleware will commit if needed
        logger.info("start: ensured user id=%s chat_id=%s", user_id, tg_id)
    except Exception:
        logger.exception("start: ensure_user failed")
        await message.answer("Server error, try again later.")
        return

    # 3) ask language (set FSM to wait)
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())  # text in english by default
    await state.set_state(LanguageSelection.select_language)
    await state.update_data(added_by=None)  # preserve ref if needed
