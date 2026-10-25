from src.http.request import Request
from src.http.response import Response
from src.http.serializer import Serializer
from src.http.parser import Parser


def test_u7_serialize_request_ends_with_crlf():
    """U7: Сериализованный Request без тела заканчивается на \\r\\n\\r\\n."""
    req = Request(method="GET", path="/test", headers={"Host": "example.com"})
    raw = Serializer.serialize(req)
    assert raw.endswith(b"\r\n\r\n")
    assert raw.startswith(b"GET /test HTTP/1.1\r\n")


def test_u8_serialize_response_has_content_length():
    """U8: В сериализованном Response всегда есть Content-Length."""
    resp = Response(status=200, reason="OK", body=b"Hello!")
    raw = Serializer.serialize(resp)
    assert b"Content-Length: 6\r\n" in raw
    assert raw.endswith(b"\r\n\r\nHello!")


def test_request_roundtrip():
    """Проверка: сериализация -> парсинг возвращает исходный запрос."""
    original = Request(
        method="POST",
        path="/api/data",
        headers={"Host": "localhost", "Content-Type": "text/plain"},
        body=b"some payload",
    )
    raw = Serializer.serialize(original)
    parsed = Parser.parse_request(raw)
    assert parsed.method == original.method
    assert parsed.path == original.path
    assert parsed.body == original.body
    assert parsed.headers["Content-Length"] == str(len(original.body))


def test_response_roundtrip():
    """Проверка: сериализация -> парсинг возвращает исходный ответ."""
    original = Response(status=404, body=b"Not Found Here")
    raw = Serializer.serialize(original)
    parsed = Parser.parse_response(raw)
    assert parsed.status == 404
    assert parsed.reason == "Not Found"
    assert parsed.body == b"Not Found Here"
