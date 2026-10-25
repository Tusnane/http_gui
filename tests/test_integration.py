from concurrent.futures import ThreadPoolExecutor
import pytest
from src.client.http_client import HttpClient
from src.http.parser import Parser
from src.http.request import Request
from src.http.serializer import Serializer
from src.net.tcp_client import TcpClient
from src.server.http_server import HttpServer

TEST_PORT = 18080
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module")
def running_server():
    server = HttpServer(host="127.0.0.1", port=TEST_PORT)
    server.start()
    yield server
    server.stop()


def test_i1_get_index(running_server):
    """I1: Сервер в потоке, HttpClient.get('/') -> 200, тело содержит 'Hello'."""
    client = HttpClient()
    resp = client.get(f"{BASE_URL}/")
    assert resp.status == 200
    assert b"Hello" in resp.body


def test_i2_post_echo(running_server):
    """I2: post('/echo', b'abc', 'text/plain') -> ответ 'abc', Content-Type сохраняется."""
    client = HttpClient()
    resp = client.post(f"{BASE_URL}/echo", b"abc", "text/plain")
    assert resp.status == 200
    assert resp.body == b"abc"
    assert resp.headers.get("Content-Type") == "text/plain"


def test_i3_get_status_404(running_server):
    """I3: get('/status/404') -> 404."""
    client = HttpClient()
    resp = client.get(f"{BASE_URL}/status/404")
    assert resp.status == 404


def test_i4_get_nonexistent(running_server):
    """I4: get('/nonexistent') -> 404."""
    client = HttpClient()
    resp = client.get(f"{BASE_URL}/nonexistent")
    assert resp.status == 404


def test_i5_100_sequential_gets(running_server):
    """I5: 100 последовательных GET -> все 200."""
    client = HttpClient()
    for _ in range(100):
        resp = client.get(f"{BASE_URL}/time")
        assert resp.status == 200


def test_i6_10_parallel_gets(running_server):
    """I6: 10 параллельных GET (потоки) -> все 200."""
    def fetch(_):
        client = HttpClient()
        return client.get(f"{BASE_URL}/headers").status

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(fetch, range(10)))

    assert statuses == [200] * 10


def test_i7_timeout_error(running_server):
    """I7: Таймаут 100 мс, сервер 'спит' 1 сек -> TimeoutError."""
    client = HttpClient(timeout_ms=100)
    with pytest.raises(TimeoutError):
        client.get(f"{BASE_URL}/sleep")


def test_i8_keep_alive_3_requests(running_server):
    """I8: keep-alive — 3 запроса в одном TCP-соединении."""
    with TcpClient.connect("127.0.0.1", TEST_PORT, timeout_ms=2000) as sock:
        for i in range(3):
            conn_val = "keep-alive" if i < 2 else "close"
            req = Request(
                method="GET",
                path="/",
                headers={"Host": f"127.0.0.1:{TEST_PORT}", "Connection": conn_val},
            )
            sock.send_all(Serializer.serialize_request(req))
            raw_resp = sock.read_http_message()
            resp = Parser.parse_response(raw_resp)
            assert resp.status == 200
            assert b"Hello" in resp.body


def test_bad_request_returns_400(running_server):
    """Проверка: некорректный запрос не роняет сервер, а возвращает 400 Bad Request."""
    with TcpClient.connect("127.0.0.1", TEST_PORT, timeout_ms=2000) as sock:
        sock.send_all(b"GARBAGE_REQUEST\r\n\r\n")
        raw_resp = sock.read_http_message()
        resp = Parser.parse_response(raw_resp)
        assert resp.status == 400
