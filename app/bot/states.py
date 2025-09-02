# app/bot/states.py
from aiogram.fsm.state import StatesGroup, State


class LanguageSelection(StatesGroup):
    select_language = State()
