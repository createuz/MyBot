# app/bot/handlers/callbacks.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.states import LanguageSelection
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_manager import RedisManager
from app.utils.user_service import upsert_user_language

router = Router()


@router.callback_query(F.data.startswith("lang:"), LanguageSelection.select_language)
async def lang_callback(call: CallbackQuery, state: FSMContext, **data):
    db = data.get("db")
    rid = data.get("request_id")
    logger = get_logger(rid)
    redis = RedisManager.client()
    lang = call.data.split(":", 1)[1]
    tg_id = call.from_user.id
    try:
        user_id = await upsert_user_language(session=db, chat_id=tg_id, language=lang)
        if db.session_created:
            db.info["committed_by_handler"] = True
            await db.commit()
        logger.info("lang_callback: upserted id=%s chat_id=%s lang=%s", user_id, tg_id, lang)
    except Exception:
        try:
            if db.session_created:
                await db.rollback()
        except Exception:
            logger.exception("rollback failed")
        await call.answer("Server error, try again later.", show_alert=True)
        return

    try:
        if redis:
            await redis.set(f"user:{tg_id}:lang", lang, ex=7 * 24 * 3600)
    except Exception:
        logger.warning("redis set failed for %s", tg_id)

    await call.answer(t(lang, "lang_set"))
    try:
        await call.message.edit_text(t(lang, "greeting"))
    except Exception:
        logger.warning("edit message failed")
    await state.clear()
