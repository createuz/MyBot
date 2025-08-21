# app/bot/handlers/callbacks.py
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.user_service import update_user_language
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.db_helpers import safe_commit_if_needed
from app.utils.redis_client import get_redis, redis_set, redis_delete
from app.utils.states import LanguageSelection

router = Router()
CACHE_TTL = 7 * 24 * 3600


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(cb: CallbackQuery, state: FSMContext, **data):
    db = data.get("db")
    logger = get_logger(data.get("request_id"))
    tg_id = cb.from_user.id
    lang = cb.data.split(":", 1)[1]

    current_state = await state.get_state()
    if current_state != LanguageSelection.waiting.state:
        await cb.answer("Please use /start to change language.", show_alert=False)
        return

    # update DB language
    await update_user_language(db, tg_id, lang)
    await safe_commit_if_needed(db)

    # update redis and remove pending
    redis = await get_redis()
    if redis:
        await redis_set(f"user:{tg_id}:lang", lang, ex=CACHE_TTL)
        await redis_delete(f"user:{tg_id}:pending_lang")

    # clear state and reply
    await state.clear()
    await cb.answer(t(lang, "lang_set"))
    try:
        await cb.message.edit_text(t(lang, "greeting"))
    except Exception:
        await cb.message.reply(t(lang, "greeting"))
