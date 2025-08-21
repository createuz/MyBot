# app/bot/handlers/start.py
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.bot.keyboards import language_keyboard
from app.bot.translations import t
from app.core.logger import get_logger
from app.db.models import User
from app.utils.db_helpers import safe_commit_if_needed
from app.utils.redis_client import RedisManager
from app.utils.states import LanguageSelection
from app.utils.user_cache import get_lang_cache_then_db

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

    # clear any previous FSM
    await state.clear()

    # 1) redis-first -> db fallback
    lang = await get_lang_cache_then_db(db, tg_id)
    if lang:
        await message.answer(t(lang, "greeting"))
        return

    # 2) No confirmed language -> ensure DB user row exists (language stays NULL)
    try:
        ins = pg_insert(User).values(
            chat_id=tg_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=None
        ).on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={
                "username": pg_insert(User).excluded.username,
                "first_name": pg_insert(User).excluded.first_name,
                "is_premium": pg_insert(User).excluded.is_premium,
            }
        ).returning(User.id)
        res = await db.execute(ins)
        _ = res.scalar_one()
    except Exception:
        logger.exception("start: ensure user insert/update failed")

    # commit only if session created & has changes
    await safe_commit_if_needed(db)

    # 3) set pending flag in redis + FSM waiting + ask language
    await RedisManager.set(f"user:{tg_id}:pending", "1", ex=PENDING_TTL)
    await state.set_state(LanguageSelection.waiting)
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
