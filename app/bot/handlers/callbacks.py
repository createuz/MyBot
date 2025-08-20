# app/bot/handlers/callbacks.py
from aiogram import Router

from app.bot.handlers.user_service import upsert_user
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_client import get_redis

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(callback, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    redis = await get_redis()

    lang = callback.data.split(":", 1)[1]
    tg_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    is_premium = getattr(callback.from_user, "is_premium", False)

    try:
        user_id = await upsert_user(session=db, chat_id=tg_id, username=username, first_name=first_name,
                                    is_premium=is_premium, language=lang)
        await db.commit()
        print(db.info["committed_by_handler"])
        db.info["committed_by_handler"] = True
        print(db.info["committed_by_handler"])
        logger.info("lang_callback: user upserted id=%s chat_id=%s lang=%s", user_id, tg_id, lang)
    except Exception:
        try:
            await db.rollback()
        except Exception:
            logger.exception("rollback failed")
        await callback.answer("Server error, try again later.", show_alert=True)
        return

    # best-effort cache
    try:
        await redis.set(f"user:{tg_id}:lang", lang, ex=7 * 24 * 3600)
    except Exception:
        logger.warning("lang_callback: redis set failed for %s", tg_id)

    try:
        await callback.answer(t(lang, "lang_set"))
        await callback.message.edit_text(t(lang, "greeting"))
    except Exception:
        logger.warning("notify failed")
