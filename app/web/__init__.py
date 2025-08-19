# app/web/__init__.py
from app.web.apps import setup_aiohttp_app

__all__ = ["setup_aiohttp_app"]
