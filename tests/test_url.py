import pytest
from src.http.url import Url, ParseError


def test_u1_url_parse_full():
    """U1: Полный разбор URL с портом, путём и query."""
    u = Url.parse("http://host:8080/path?q=1")
    assert u.scheme == "http"
    assert u.host == "host"
    assert u.port == 8080
    assert u.path == "/path"
    assert u.query == "q=1"
    assert u.full_path == "/path?q=1"


def test_u2_url_default_port():
    """U2: Порт по умолчанию 80 для http."""
    u = Url.parse("http://host/path")
    assert u.host == "host"
    assert u.port == 80
    assert u.path == "/path"
    assert u.query == ""


def test_u3_url_garbage():
    """U3: Мусорная строка вызывает ParseError."""
    with pytest.raises(ParseError):
        Url.parse("garbage")


def test_url_https_default_port():
    u = Url.parse("https://secure.example.com")
    assert u.scheme == "https"
    assert u.port == 443
    assert u.path == "/"


def test_url_invalid_port():
    with pytest.raises(ParseError):
        Url.parse("http://host:99999/path")

    with pytest.raises(ParseError):
        Url.parse("http://host:abc/path")


def test_url_empty_or_unsupported_scheme():
    with pytest.raises(ParseError):
        Url.parse("")
    with pytest.raises(ParseError):
        Url.parse("ftp://files.com/doc")

def test_url_with_root_query():
    u = Url.parse("http://localhost?debug=true")
    assert u.path == "/"
    assert u.query == "debug=true"
    assert u.full_path == "/?debug=true"


def test_url_missing_host_raises():
    with pytest.raises(ParseError):
        Url.parse("http:///path")