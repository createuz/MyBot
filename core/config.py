import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str = os.getenv("PG_HOST")
    port: int = int(os.getenv("PG_PORT"))
    user: str = os.getenv("PG_USER")
    password: str = os.getenv("PG_PASSWORD")
    name: str = os.getenv("PG_NAME")
    driver: str = os.getenv("DB_DRIVER")
    db_system: str = os.getenv("DB_SYSTEM")

    def build_db_url(self) -> str:
        return URL.create(
            drivername=f"{self.db_system}+{self.driver}",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        ).render_as_string(hide_password=False)


@dataclass
class BotConfig:
    token: str = os.getenv("BOT_TOKEN")
    reds_url: str = os.getenv("REDIS_URL")
    db_pool_max: int = os.getenv("DB_POOL_MAX")
    db_pool_min: int = os.getenv("DB_POOL_MIN")
    pg_max_connection: int = os.getenv("PG_MAX_CONNECTIONS")


@dataclass
class AppConfig:
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    bot: BotConfig = field(default_factory=BotConfig)


conf: AppConfig = AppConfig()
# bot: Bot = Bot(token=conf.bot_token.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# print("Database URL:", conf.db.build_db_url())
