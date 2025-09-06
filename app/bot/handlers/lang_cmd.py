from aiogram import Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.kb.keyboards import language_keyboard
from app.bot.kb.states import LanguageSelection
from app.core.logger import get_logger
from app.utils.redis_manager import RedisManager
from app.utils.user_service import get_lang_cache_then_db

router = Router()


@router.message(Command("lang"))
async def lang_command(message: Message, state: FSMContext, **data):
    db = data.get("db")
    rid = data.get("request_id")
    logger = get_logger(rid)
    tg_id = message.from_user.id
    redis = RedisManager.client()
    lang = await get_lang_cache_then_db(session=db, redis_client=redis, chat_id=tg_id)
    await message.answer(f"Your current language: {lang or 'not set'}", reply_markup=language_keyboard())
    await state.set_state(LanguageSelection.select_language)
