from dataclasses import dataclass


class ParseError(Exception):
    """Ошибка разбора URL или HTTP-сообщения."""
    pass


class HttpError(Exception):
    """Ошибка протокола HTTP с кодом статуса."""
    def __init__(self, status: int, message: str = ""):
        super().__init__(message or f"HTTP Error {status}")
        self.status = status


@dataclass
class Url:
    scheme: str
    host: str
    port: int
    path: str
    query: str = ""

    @classmethod
    def parse(cls, raw_url: str) -> "Url":
        if not raw_url or not isinstance(raw_url, str):
            raise ParseError("Пустой URL")

        raw_url = raw_url.strip()
        if "://" not in raw_url:
            raise ParseError("Отсутствует схема (http:// или https://)")

        scheme, rest = raw_url.split("://", 1)
        scheme = scheme.lower()
        if scheme not in ("http", "https"):
            raise ParseError(f"Неподдерживаемая схема: {scheme}")

        # Отделяем query (?param=1)
        query = ""
        if "?" in rest:
            rest, query = rest.split("?", 1)

        # Отделяем путь (/path) от хоста
        if "/" in rest:
            host_port, path_part = rest.split("/", 1)
            path = "/" + path_part
        else:
            host_port = rest
            path = "/"

        if not host_port:
            raise ParseError("Отсутствует хост")

        # Разбираем хост и порт
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            if not host:
                raise ParseError("Пустой хост")
            try:
                port = int(port_str)
            except ValueError as exc:
                raise ParseError(f"Некорректный порт: {port_str}") from exc
            if not (1 <= port <= 65535):
                raise ParseError(f"Порт вне диапазона 1-65535: {port}")
        else:
            host = host_port
            port = 443 if scheme == "https" else 80

        return cls(
            scheme=scheme,
            host=host,
            port=port,
            path=path,
            query=query,
        )

    @property
    def full_path(self) -> str:
        """Путь вместе с query-параметрами для отправки в HTTP-запросе."""
        return f"{self.path}?{self.query}" if self.query else self.path
