# app/bot/handlers/callbacks.py
from aiogram import Router, types
from bot.translations import t
from utils.redis_client import get_redis
from utils.user_service import upsert_user
from core.logger import get_logger

router = Router()

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(callback: types.CallbackQuery, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    redis = await get_redis()

    lang = callback.data.split(":", 1)[1]
    tg_id = callback.from_user.id
    username = callback.message.from_user.username if callback.message.from_user else None
    first_name = callback.message.from_user.first_name if callback.message.from_user else None
    is_premium = getattr(callback.from_user, "is_premium", False)

    # 1) Upsert DB (atomic). We'll commit now to guarantee DB persistence before caching.
    try:
        user_id = await upsert_user(
            session=db,
            chat_id=tg_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=lang,
            added_by=None
        )
        await db.commit()  # explicitly ensure persistence before caching
        logger.info(f"User language upserted, id={user_id}, lang={lang}")
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to upsert language for {tg_id}: {e}")
        await callback.answer("Server error, try again later.", show_alert=True)
        return

    # 2) Update Redis cache (best-effort)
    try:
        await redis.set(f"user:{tg_id}:lang", lang, ex=7 * 24 * 3600)
    except Exception as e:
        logger.error(f"Redis SET failed for {tg_id}: {e}")

    # 3) Reply user in selected language
    await callback.answer(t(lang, "lang_set"), show_alert=False)
    try:
        await callback.message.edit_text(t(lang, "greeting"))
    except Exception:
        # editing may fail for old messages — ignore
        pass
