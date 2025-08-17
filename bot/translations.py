# app/bot/translations.py
TRANSLATIONS = {
    "en": {
        "welcome": "Welcome! Choose your language:",
        "lang_set": "Language set to English ✅",
        "greeting": "Hello! Welcome to the bot."
    },
    "uz": {
        "welcome": "Xush kelibsiz! Tilni tanlang:",
        "lang_set": "Til o‘zgartirildi: O‘zbekcha ✅",
        "greeting": "Salom! Botga xush kelibsiz."
    },
    "ru": {
        "welcome": "Добро пожаловать! Выберите язык:",
        "lang_set": "Язык установлен: Русский ✅",
        "greeting": "Привет! Добро пожаловать в бота."
    }
}

def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, "")
