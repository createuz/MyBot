# app/bot/handlers/lang_cmd.py
from aiogram import Router, types
from aiogram.filters.command import Command

from app.bot.handlers.user_service import get_lang_cache_then_db
from app.bot.keyboards import language_keyboard
from app.core.logger import get_logger
from app.utils.redis_client import get_redis

router = Router()


@router.message(Command("lang"))
async def lang_command(message: types.Message, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id

    redis = await get_redis()
    lang = await get_lang_cache_then_db(db, redis, tg_id)
    await message.answer(f"Your current language: {lang or 'en'}\nChoose new:", reply_markup=language_keyboard())
