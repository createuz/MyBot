# app/web/health.py
from aiohttp import web


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def register(app: web.Application) -> None:
    app.router.add_get("/healthz", health)
