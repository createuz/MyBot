# app/bot/handlers/start.py
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from app.bot.handlers.user_service import get_lang_cache_then_db, ensure_user_insert_if_missing
from app.bot.keyboards import language_keyboard
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.db_helpers import safe_commit_if_needed
from app.utils.redis_client import get_redis, redis_set
from app.utils.states import LanguageSelection

router = Router()

PENDING_TTL = 24 * 3600


@router.message(Command("start"))
async def start_handler(message, state: FSMContext, **data):
    db = data.get("db")  # LazySessionProxy
    logger = get_logger(data.get("request_id"))
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    # clear any FSM state on /start
    await state.clear()

    redis = await get_redis()

    # 1) redis-first
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    if lang:
        await message.answer(t(lang, "greeting"))
        return

    # 2) user exists in DB but language is NULL OR user not exists -> ensure user record (language NULL)
    await ensure_user_insert_if_missing(db, tg_id, username, first_name, is_premium)
    # commit only if session actually created & has changes
    await safe_commit_if_needed(db)

    # 3) set pending flag in redis and set FSM waiting, then ask language
    if redis:
        await redis_set(f"user:{tg_id}:pending_lang", "1", ex=PENDING_TTL)
    await state.set_state(LanguageSelection.waiting)
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
