# app/bot/handlers/callbacks.py
from aiogram import Router, types

from app.bot.handlers.user_service import upsert_user
from app.bot.translations import t
from app.core.logger import get_logger
from app.utils.redis_client import get_redis

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(callback: types.CallbackQuery, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    redis = await get_redis()

    lang = callback.data.split(":", 1)[1]
    tg_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    is_premium = getattr(callback.from_user, "is_premium", False)

    # upsert and commit immediately (DB-first -> cache)
    try:
        user_id = await upsert_user(session=db, chat_id=tg_id, username=username,
                                    first_name=first_name, is_premium=is_premium,
                                    language=lang, added_by=None)
        await db.commit()
        db.info["committed_by_handler"] = True
        logger.info(f"User upserted and committed id={user_id}, chat_id={tg_id}, lang={lang}")
    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            logger.exception("Rollback failed in handler")
        logger.exception(f"Failed to upsert/commit language for {tg_id}: {e}")
        await callback.answer("Server error, please try again later.", show_alert=True)
        return

    # update redis (best-effort)
    try:
        await redis.set(f"user:{tg_id}:lang", lang, ex=7 * 24 * 3600)
    except Exception as e:
        logger.warning(f"Redis SET failed for {tg_id}: {e}")

    await callback.answer(t(lang, "lang_set"))
    try:
        await callback.message.edit_text(t(lang, "greeting"))
    except Exception:
        pass
