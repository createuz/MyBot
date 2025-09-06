# app/bot/translations.py
langs_text = {
    "en": {"welcome": "Choose language", "greeting": "Welcome back!", "lang_set": "Language set"},
    "uz": {"welcome": "Tilni tanlang", "greeting": "Xush kelibsiz!", "lang_set": "Til saqlandi"},
    "ru": {"welcome": "Выберите язык", "greeting": "Добро пожаловать!", "lang_set": "Язык сохранён"},
}


def t(lang: str, key: str) -> str:
    return langs_text.get(lang, langs_text["en"]).get(key, "")
