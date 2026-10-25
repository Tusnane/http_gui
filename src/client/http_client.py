from typing import Dict, Optional
from src.http.url import Url, ParseError
from src.http.request import Request
from src.http.response import Response
from src.http.serializer import Serializer
from src.http.parser import Parser
from src.net.tcp_client import TcpClient


class HttpClient:
    """HTTP-клиент для выполнения GET и POST запросов поверх сокетов."""

    def __init__(self, timeout_ms: int = 5000, max_redirects: int = 5):
        self.timeout_ms = timeout_ms
        self.max_redirects = max_redirects

    def set_timeout(self, ms: int) -> None:
        if ms <= 0:
            raise ValueError("Таймаут должен быть положительным числом")
        self.timeout_ms = ms

    def follow_redirects(self, max_redirects: int) -> None:
        self.max_redirects = max(0, max_redirects)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        return self._request("GET", url, headers=headers)

    def post(
        self,
        url: str,
        body: bytes | str = b"",
        content_type: str = "text/plain; charset=utf-8",
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        req_headers = dict(headers) if headers else {}
        if content_type and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = content_type
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        return self._request("POST", url, headers=req_headers, body=body_bytes)

    def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: bytes = b"",
        redirects_left: Optional[int] = None,
    ) -> Response:
        if redirects_left is None:
            redirects_left = self.max_redirects

        parsed_url = Url.parse(url)
        req_headers = dict(headers) if headers else {}

        # Формируем обязательный заголовок Host
        default_port = 443 if parsed_url.scheme == "https" else 80
        if parsed_url.port != default_port:
            req_headers.setdefault("Host", f"{parsed_url.host}:{parsed_url.port}")
        else:
            req_headers.setdefault("Host", parsed_url.host)

        req_headers.setdefault("Connection", "close")
        req_headers.setdefault("User-Agent", "PythonSocketHttpClient/1.0")

        req = Request(
            method=method.upper(),
            path=parsed_url.full_path,
            headers=req_headers,
            body=body,
        )
        raw_req = Serializer.serialize_request(req)

        use_ssl = parsed_url.scheme == "https"
        with TcpClient.connect(parsed_url.host, parsed_url.port, self.timeout_ms, use_ssl=use_ssl) as sock:
            sock.send_all(raw_req)
            raw_resp = sock.read_http_message()
            if not raw_resp:
                raise ParseError("Сервер закрыл соединение, не отправив ответ")
            resp = Parser.parse_response(raw_resp)

        # Обработка редиректов 301, 302, 307 (Бонус + Вопрос №6)
        if resp.status in (301, 302, 307) and redirects_left > 0:
            location = None
            for k, v in resp.headers.items():
                if k.lower() == "location":
                    location = v
                    break
            if location:
                if location.startswith("/"):
                    location = f"{parsed_url.scheme}://{parsed_url.host}:{parsed_url.port}{location}"
                # Для 301/302 меняем метод на GET, для 307 сохраняем исходный метод
                next_method = method if resp.status == 307 else "GET"
                next_body = body if resp.status == 307 else b""
                return self._request(next_method, location, headers, next_body, redirects_left - 1)

        return resp
