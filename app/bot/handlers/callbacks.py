# app/bot/handlers/callbacks.py
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.bot.translations import t
from app.core.logger import get_logger
from app.db.models import User
from app.utils.db_helpers import safe_commit_if_needed
from app.utils.redis_client import RedisManager
from app.utils.states import LanguageSelection

router = Router()
CACHE_TTL = 7 * 24 * 3600


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(cb: CallbackQuery, state: FSMContext, **data):
    db = data.get("db")
    logger = get_logger(data.get("request_id"))
    tg_id = cb.from_user.id
    lang = cb.data.split(":", 1)[1]

    # require waiting state
    if await state.get_state() != LanguageSelection.waiting.state:
        await cb.answer("Please send /start to begin.", show_alert=False)
        return

    # update DB language
    try:
        ins = pg_insert(User).values(chat_id=tg_id, language=lang).on_conflict_do_update(
            index_elements=[User.chat_id], set_={"language": pg_insert(User).excluded.language}
        ).returning(User.id)
        res = await db.execute(ins)
        _ = res.scalar_one()
    except Exception:
        logger.exception("lang_callback: DB update failed")
        # continue to set redis optimistically

    await safe_commit_if_needed(db)

    # update redis and remove pending
    await RedisManager.set(f"user:{tg_id}:lang", lang, ex=CACHE_TTL)
    await RedisManager.delete(f"user:{tg_id}:pending")

    # clear state and reply
    await state.clear()
    await cb.answer(t(lang, "lang_set"))
    try:
        await cb.message.edit_text(t(lang, "greeting"))
    except Exception:
        await cb.message.reply(t(lang, "greeting"))
