# app/bot/handlers/lang_cmd.py
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from app.bot.handlers.user_service import get_lang_cache_then_db
from app.bot.keyboards import language_keyboard
from app.utils.redis_client import get_redis, redis_get
from app.utils.states import LanguageSelection

router = Router()


@router.message(Command("lang"))
async def lang_command(message, state: FSMContext, **data):
    db = data.get("db")
    tg_id = message.from_user.id

    redis = await get_redis()
    pending = await redis_get(f"user:{tg_id}:pending_lang") if redis else None
    if pending:
        await state.set_state(LanguageSelection.waiting)  # or import class and use .waiting
        await message.answer("Please choose your language:", reply_markup=language_keyboard())
        return

    lang = await get_lang_cache_then_db(db, redis, tg_id)
    await message.answer(f"Your current language: {lang or 'not set'}\nChoose new:", reply_markup=language_keyboard())
