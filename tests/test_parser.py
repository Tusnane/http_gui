import pytest
from src.http.parser import Parser
from src.http.url import ParseError


def test_u4_parse_simple_get():
    """U4: Простой GET-запрос."""
    raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    req = Parser.parse_request(raw)
    assert req.method == "GET"
    assert req.path == "/"
    assert req.version == "HTTP/1.1"
    assert req.headers["Host"] == "localhost"
    assert req.body == b""


def test_u5_parse_request_with_body():
    """U5: Запрос с телом и Content-Length."""
    raw = (
        b"POST /echo HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 5\r\n"
        b"\r\n"
        b"helloEXTRA_BYTES"
    )
    req = Parser.parse_request(raw)
    assert req.method == "POST"
    assert req.body == b"hello"


def test_u6_parse_request_without_host():
    """U6: В HTTP/1.1 запрос без заголовка Host вызывает ParseError."""
    raw = b"GET / HTTP/1.1\r\nUser-Agent: test\r\n\r\n"
    with pytest.raises(ParseError):
        Parser.parse_request(raw)


def test_u9_parse_response_chunked():
    """U9: Сборка тела ответа с Transfer-Encoding: chunked."""
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"5\r\nhello\r\n"
        b"6\r\n world\r\n"
        b"0\r\n\r\n"
    )
    resp = Parser.parse_response(raw)
    assert resp.status == 200
    assert resp.body == b"hello world"


def test_u10_header_overflow():
    """U10: Заголовок больше 8 КБ вызывает ParseError."""
    huge_header = b"X-Huge: " + (b"A" * 9000) + b"\r\n"
    raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n" + huge_header + b"\r\n"
    with pytest.raises(ParseError):
        Parser.parse_request(raw)


def test_smuggling_protection():
    """Защита от одновременного Content-Length и Transfer-Encoding."""
    raw = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 5\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n"
        b"0\r\n\r\n"
    )
    with pytest.raises(ParseError):
        Parser.parse_request(raw)


def test_incomplete_body_raises_error():
    raw = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 100\r\n\r\n"
        b"short"
    )
    with pytest.raises(ParseError):
        Parser.parse_request(raw)


def test_malformed_start_line():
    with pytest.raises(ParseError):
        Parser.parse_request(b"INVALID_LINE\r\n\r\n")
