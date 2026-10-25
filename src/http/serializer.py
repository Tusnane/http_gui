from abc import ABC, abstractmethod
from email.utils import formatdate
from .request import Request
from .response import Response


class BaseSerializer(ABC):
    """Абстрактный интерфейс сериализатора (для выполнения требования ООП)."""

    @staticmethod
    @abstractmethod
    def serialize_request(req: Request) -> bytes:
        pass

    @staticmethod
    @abstractmethod
    def serialize_response(resp: Response) -> bytes:
        pass


class Serializer(BaseSerializer):
    @staticmethod
    def serialize_request(req: Request) -> bytes:
        headers = dict(req.headers)
        if req.body and "Content-Length" not in headers:
            headers["Content-Length"] = str(len(req.body))

        lines = [f"{req.method.upper()} {req.path} {req.version}"]
        for key, value in headers.items():
            lines.append(f"{key}: {value}")

        header_bytes = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
        return header_bytes + req.body

    @staticmethod
    def serialize_response(resp: Response) -> bytes:
        headers = dict(resp.headers)
        # По ТЗ в ответе всегда должен быть Content-Length (тест U8)
        if "Content-Length" not in headers:
            headers["Content-Length"] = str(len(resp.body))
        if "Date" not in headers:
            headers["Date"] = formatdate(timeval=None, localtime=False, usegmt=True)

        reason = resp.reason or "OK"
        lines = [f"{resp.version} {resp.status} {reason}"]
        for key, value in headers.items():
            lines.append(f"{key}: {value}")

        header_bytes = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
        return header_bytes + resp.body

    @classmethod
    def serialize(cls, obj: Request | Response) -> bytes:
        """Универсальный метод для удобства тестов (U7, U8)."""
        if isinstance(obj, Request):
            return cls.serialize_request(obj)
        if isinstance(obj, Response):
            return cls.serialize_response(obj)
        raise TypeError("Ожидался объект Request или Response")
