from typing import Callable, Dict, Tuple
from src.http.request import Request
from src.http.response import Response

Handler = Callable[[Request], Response]


class Router:
    """Маршрутизатор входящих HTTP-запросов."""

    def __init__(self):
        self._routes: Dict[Tuple[str, str], Handler] = {}

    def route(self, method: str, path: str, handler: Handler) -> None:
        self._routes[(method.upper(), path)] = handler

    def dispatch(self, req: Request) -> Response:
        clean_path = req.path.split("?", 1)[0]
        key = (req.method.upper(), clean_path)
        if key in self._routes:
            return self._routes[key](req)

        # Динамический маршрут /status/{code}
        if req.method.upper() == "GET" and clean_path.startswith("/status/"):
            parts = clean_path.split("/")
            if len(parts) == 3:
                try:
                    code = int(parts[2])
                    return Response(
                        status=code,
                        headers={"Content-Type": "text/plain; charset=utf-8"},
                        body=f"Status {code}".encode("utf-8"),
                    )
                except ValueError:
                    pass

        return Response(
            status=404,
            reason="Not Found",
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=b"404 Not Found",
        )
