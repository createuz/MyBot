# app/bot/handlers/callbacks.py
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_manager import RedisManager
from app.utils.states import LanguageSelection
from app.utils.user_service import upsert_user_language

router = Router()


@router.callback_query(
    StateFilter(LanguageSelection.select_language),
    F.data.startswith("lang:")
)
async def lang_callback(call: CallbackQuery, state: FSMContext, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    redis = RedisManager.client()

    lang = call.data.split(":", 1)[1]
    tg_id = call.from_user.id

    try:
        # update DB language
        user_id = await upsert_user_language(session=db, chat_id=tg_id, language=lang)
        # mark as committed by handler so middleware won't commit double
        if db.session_created:
            db.info["committed_by_handler"] = True
        # ensure persistence immediately (optionally call commit here if you prefer)
        if db.session_created:
            await db.commit()  # safe: middleware checks flag and will skip second commit
        logger.info("lang_callback: user upserted id=%s chat_id=%s lang=%s", user_id, tg_id, lang)
    except Exception:
        try:
            if db.session_created:
                await db.rollback()
        except Exception:
            logger.exception("rollback failed")
        await call.answer("Server error, try again later.", show_alert=True)
        return

    # cache to redis (best-effort)
    try:
        if redis is not None:
            await redis.set(f"user:{tg_id}:lang", lang, ex=7 * 24 * 3600)
    except Exception:
        logger.warning("lang_callback: redis set failed for %s", tg_id)

    await call.answer(t(lang, "lang_set"))
    await call.message.edit_text(t(lang, "greeting"))
    await state.clear()
