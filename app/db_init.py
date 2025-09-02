# app/db_init.py
import asyncio
import sys
from typing import Optional

from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import init_db

logger = get_logger()
import os

here = os.path.dirname(os.path.dirname(__file__))  # repo root

# --- patch snippet for app/db_init.py ---
import os


# 'here' already defined as repo root


def _run_alembic_upgrade() -> bool:
    """
    Try to run `alembic upgrade head` programmatically.
    If alembic package not installed OR alembic folder does not exist => skip.
    Returns True on success, False otherwise (fallback will run).
    """
    try:
        from alembic.config import Config
        from alembic import command
    except Exception as e:
        logger.warning("alembic not available: %s", e)
        return False

    # --- NEW: check that alembic scripts folder exists before attempting ---
    alembic_folder = os.path.join(here, "alembic")
    if not os.path.isdir(alembic_folder):
        logger.info("Alembic directory not found (%s) — skipping alembic upgrade", alembic_folder)
        return False
    # -----------------------------------------------------------------------

    try:
        alembic_ini = os.path.join(here, "alembic.ini")
        cfg = Config(alembic_ini)
        if not cfg.get_main_option("script_location"):
            cfg.set_main_option("script_location", "alembic")
        # set DB URL from your conf object (adjust method name if different)
        cfg.set_main_option("sqlalchemy.url", conf.db.sqlalchemy_url())
        logger.info("Running alembic upgrade head (alembic.ini -> %s)", conf.db.sqlalchemy_url())
        command.upgrade(cfg, "head")
        logger.info("Alembic upgrade finished")
        return True
    except Exception as e:
        logger.exception("Alembic upgrade failed: %s", e)
        return False


async def _fallback_create_all():
    """
    Fallback: use SQLAlchemy create_all() (sync-to-async via session.init_db)
    """
    logger.info("Falling back to create_all() via init_db()")
    try:
        await init_db()
        logger.info("create_all(): OK")
    except Exception as e:
        logger.exception("create_all() failed: %s", e)
        raise


async def main(seed_admin: Optional[int] = None):
    """
    Run migrations (alembic if available), otherwise do create_all().
    Optionally can seed an admin user if desired (not implemented here).
    """
    ok = _run_alembic_upgrade()
    if not ok:
        await _fallback_create_all()

    # optional: seed initial data (admin). Add your seeding code here if needed.
    # Example (pseudo):
    # if seed_admin:
    #     async with AsyncSessionLocal() as s:
    #         await seed_admin_user(s, seed_admin)

    logger.info("DB init finished.")


if __name__ == "__main__":
    # run with: python -m app.db_init  OR python app/db_init.py
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception("db_init failed: %s", e)
        sys.exit(2)
