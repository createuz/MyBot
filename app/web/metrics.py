# app/web/metrics.py
from aiohttp import web
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, Histogram

# minimal registry (you can use a global registry if preferred)
REGISTRY = CollectorRegistry()
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"], registry=REGISTRY)
WEBHOOK_UPDATES = Counter("telegram_webhook_updates_total", "Telegram webhook updates received", registry=REGISTRY)
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "HTTP request latency seconds", ["endpoint"], registry=REGISTRY)


async def metrics_handler(request: web.Request) -> web.Response:
    data = generate_latest(REGISTRY)
    return web.Response(body=data, content_type=CONTENT_TYPE_LATEST)


def register(app: web.Application) -> None:
    # Expose Prometheus metrics on /metrics
    app.router.add_get("/metrics", metrics_handler)
