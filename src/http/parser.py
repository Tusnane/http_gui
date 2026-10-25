from abc import ABC, abstractmethod
from typing import Dict, Tuple
from .request import Request
from .response import Response
from .url import ParseError

MAX_HEADER_SIZE = 8192  # 8 КБ по тесту U10


class BaseParser(ABC):
    """Абстрактный интерфейс парсера."""

    @staticmethod
    @abstractmethod
    def parse_request(raw: bytes) -> Request:
        pass

    @staticmethod
    @abstractmethod
    def parse_response(raw: bytes) -> Response:
        pass


class Parser(BaseParser):
    @staticmethod
    def _split_headers_body(raw: bytes) -> Tuple[bytes, bytes]:
        if not raw:
            raise ParseError("Пустое сообщение")

        sep_idx = raw.find(b"\r\n\r\n")
        if sep_idx == -1:
            if len(raw) > MAX_HEADER_SIZE:
                raise ParseError("Превышен максимальный размер заголовков (8 КБ)")
            raise ParseError("Не найден конец заголовков (\\r\\n\\r\\n)")

        if sep_idx > MAX_HEADER_SIZE:
            raise ParseError("Превышен максимальный размер заголовков (8 КБ)")

        header_bytes = raw[:sep_idx]
        body_bytes = raw[sep_idx + 4:]
        return header_bytes, body_bytes

    @staticmethod
    def _parse_headers(lines: list[str]) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for line in lines:
            if ":" not in line:
                raise ParseError(f"Некорректная строка заголовка: {line}")
            key, val = line.split(":", 1)
            key = key.strip()
            if not key:
                raise ParseError("Пустое имя заголовка")
            headers[key] = val.strip()
        return headers

    @staticmethod
    def _decode_chunked(body: bytes) -> bytes:
        result = bytearray()
        pos = 0
        while True:
            line_end = body.find(b"\r\n", pos)
            if line_end == -1:
                raise ParseError("Некорректный chunked-поток: нет \\r\\n после размера")

            size_str = body[pos:line_end].decode("ascii", errors="replace").split(";")[0].strip()
            try:
                chunk_size = int(size_str, 16)
            except ValueError as exc:
                raise ParseError(f"Некорректный размер чанка: {size_str}") from exc

            pos = line_end + 2
            if chunk_size == 0:
                break

            if pos + chunk_size > len(body):
                raise ParseError("Неполный чанк в теле сообщения")

            result.extend(body[pos:pos + chunk_size])
            pos += chunk_size

            if body[pos:pos + 2] != b"\r\n":
                raise ParseError("Отсутствует \\r\\n после данных чанка")
            pos += 2

        return bytes(result)

    @classmethod
    def _extract_body(cls, headers: Dict[str, str], raw_body: bytes) -> bytes:
        lower_headers = {k.lower(): v for k, v in headers.items()}

        has_cl = "content-length" in lower_headers
        has_te = "transfer-encoding" in lower_headers

        # Защита от HTTP Request Smuggling (Вопрос 28)
        if has_cl and has_te:
            raise ParseError("Одновременное использование Content-Length и Transfer-Encoding запрещено")

        if has_te and "chunked" in lower_headers["transfer-encoding"].lower():
            return cls._decode_chunked(raw_body)

        if has_cl:
            try:
                length = int(lower_headers["content-length"])
            except ValueError as exc:
                raise ParseError("Некорректный Content-Length") from exc
            if length < 0:
                raise ParseError("Отрицательный Content-Length")
            if len(raw_body) < length:
                raise ParseError("Тело сообщения меньше указанного Content-Length")
            return raw_body[:length]

        return raw_body

    @classmethod
    def parse_request(cls, raw: bytes) -> Request:
        header_bytes, raw_body = cls._split_headers_body(raw)
        try:
            text = header_bytes.decode("iso-8859-1")
        except UnicodeDecodeError as exc:
            raise ParseError("Ошибка декодирования заголовков") from exc

        lines = text.split("\r\n")
        start_line = lines[0]
        parts = start_line.split(" ")
        if len(parts) != 3:
            raise ParseError(f"Некорректная стартовая строка запроса: {start_line}")

        method, path, version = parts
        if not path.startswith("/"):
            raise ParseError("Путь запроса должен начинаться с '/'")
        if not version.startswith("HTTP/"):
            raise ParseError(f"Некорректная версия протокола: {version}")

        headers = cls._parse_headers(lines[1:])

        # В HTTP/1.1 заголовок Host обязателен (Тест U6 и Вопрос 1)
        lower_keys = {k.lower() for k in headers}
        if version == "HTTP/1.1" and "host" not in lower_keys:
            raise ParseError("В HTTP/1.1 обязателен заголовок Host")

        body = cls._extract_body(headers, raw_body)
        return Request(method=method.upper(), path=path, version=version, headers=headers, body=body)

    @classmethod
    def parse_response(cls, raw: bytes) -> Response:
        header_bytes, raw_body = cls._split_headers_body(raw)
        try:
            text = header_bytes.decode("iso-8859-1")
        except UnicodeDecodeError as exc:
            raise ParseError("Ошибка декодирования заголовков ответа") from exc

        lines = text.split("\r\n")
        start_line = lines[0]
        parts = start_line.split(" ", 2)
        if len(parts) < 2:
            raise ParseError(f"Некорректная строка статуса: {start_line}")

        version = parts[0]
        if not version.startswith("HTTP/"):
            raise ParseError(f"Некорректная версия протокола: {version}")

        try:
            status = int(parts[1])
        except ValueError as exc:
            raise ParseError(f"Статус должен быть числом: {parts[1]}") from exc

        reason = parts[2] if len(parts) > 2 else ""
        headers = cls._parse_headers(lines[1:])
        body = cls._extract_body(headers, raw_body)

        return Response(status=status, reason=reason, version=version, headers=headers, body=body)
