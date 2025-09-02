# app/bot/handlers/lang_cmd.py
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import language_keyboard
from app.core.logger import get_logger
from app.utils.redis_manager import RedisManager
from app.utils.user_cache import get_lang_cache_then_db

router = Router()


@router.message(Command("lang"))
async def lang_command(message, state: FSMContext, **data):
    db = data.get("db")
    tg_id = message.from_user.id
    logger = get_logger(data.get("request_id"))

    # if pending -> ask and set state
    pending = await RedisManager.get(f"user:{tg_id}:pending")
    if pending:
        await state.set_state("LanguageSelection:waiting")
        await message.answer("Please choose a language:", reply_markup=language_keyboard())
        return

    lang = await get_lang_cache_then_db(db, tg_id)
    await message.answer(f"Your current language: {lang or 'not set'}\nChoose new:", reply_markup=language_keyboard())
