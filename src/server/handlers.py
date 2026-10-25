import json
import time
from datetime import datetime, timezone
from src.http.request import Request
from src.http.response import Response
from .router import Router


def handle_index(req: Request) -> Response:
    html = "<html><body><h1>Hello</h1></body></html>"
    return Response(
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        body=html.encode("utf-8"),
    )


def handle_echo(req: Request) -> Response:
    content_type = "text/plain; charset=utf-8"
    for k, v in req.headers.items():
        if k.lower() == "content-type":
            content_type = v
            break
    return Response(
        status=200,
        headers={"Content-Type": content_type},
        body=req.body,
    )


def handle_time(req: Request) -> Response:
    payload = {"time": datetime.now(timezone.utc).isoformat()}
    return Response(
        status=200,
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(payload).encode("utf-8"),
    )


def handle_headers(req: Request) -> Response:
    return Response(
        status=200,
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(req.headers, ensure_ascii=False).encode("utf-8"),
    )


def handle_sleep(req: Request) -> Response:
    """Вспомогательный маршрут для интеграционного теста с таймаутом."""
    time.sleep(1.0)
    return Response(status=200, body=b"Slept 1s")


def create_default_router() -> Router:
    router = Router()
    router.route("GET", "/", handle_index)
    router.route("POST", "/echo", handle_echo)
    router.route("GET", "/time", handle_time)
    router.route("GET", "/headers", handle_headers)
    router.route("GET", "/sleep", handle_sleep)
    return router
