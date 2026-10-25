import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from src.http.parser import Parser
from src.http.response import Response
from src.http.serializer import Serializer
from src.http.url import ParseError
from src.net.socket_wrapper import Socket
from src.net.tcp_server import TcpServer
from .handlers import create_default_router
from .router import Router

logger = logging.getLogger("http_gui")


@dataclass
class LogEntry:
    timestamp: str
    method: str
    path: str
    status: int
    duration_ms: float


class HttpServer:
    """Многопоточный HTTP-сервер с поддержкой keep-alive и очередью логов для GUI."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        router: Router | None = None,
        log_queue: queue.Queue | None = None,
        max_workers: int = 20,
    ):
        self.host = host
        self.port = port
        self.router = router or create_default_router()
        self.log_queue = log_queue if log_queue is not None else queue.Queue()
        self.max_workers = max_workers

        self._tcp_server: TcpServer | None = None
        self._thread: threading.Thread | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._running = threading.Event()
        self._log_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def start(self) -> None:
        if self.is_running:
            return
        self._tcp_server = TcpServer(self.host, self.port)
        self._tcp_server.start()
        self._running.set()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._thread = threading.Thread(target=self._AcceptLoop, daemon=True)
        self._thread.start()
        logger.info("Сервер запущен на %s:%d", self.host, self.port)

    def stop(self) -> None:
        if not self.is_running:
            return
        self._running.clear()
        if self._tcp_server:
            self._tcp_server.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        logger.info("Сервер остановлен")

    def _AcceptLoop(self) -> None:
        while self._running.is_set():
            if self._tcp_server is None:
                break
            accepted = self._tcp_server.accept()
            if accepted is None:
                continue
            client_sock, _ = accepted
            if self._executor and self._running.is_set():
                self._executor.submit(self._handle_client, client_sock)
            else:
                client_sock.close()

    def _handle_client(self, sock: Socket) -> None:
        with sock:
            sock.settimeout(5.0)
            while self._running.is_set():
                start_time = time.perf_counter()
                method = "UNKNOWN"
                path = "-"
                keep_alive = False

                try:
                    raw_req = sock.read_http_message()
                    if not raw_req:
                        break
                    start_time = time.perf_counter()
                    req = Parser.parse_request(raw_req)
                    method = req.method
                    path = req.path

                    conn_hdr = ""
                    for k, v in req.headers.items():
                        if k.lower() == "connection":
                            conn_hdr = v.lower()
                            break

                    if req.version == "HTTP/1.1":
                        keep_alive = conn_hdr != "close"
                    else:
                        keep_alive = conn_hdr == "keep-alive"

                    # Защита от Path Traversal (Вопрос №29)
                    if ".." in req.path:
                        resp = Response(status=400, reason="Bad Request", body=b"Path traversal detected")
                        keep_alive = False
                    else:
                        resp = self.router.dispatch(req)

                except ParseError as exc:
                    resp = Response(
                        status=400,
                        reason="Bad Request",
                        headers={"Content-Type": "text/plain; charset=utf-8"},
                        body=f"400 Bad Request: {exc}".encode("utf-8"),
                    )
                    keep_alive = False
                except (TimeoutError, ConnectionError):
                    break
                except Exception as exc:
                    logger.exception("Внутренняя ошибка сервера: %s", exc)
                    resp = Response(status=500, reason="Internal Server Error", body=b"500 Internal Server Error")
                    keep_alive = False

                resp.headers["Connection"] = "keep-alive" if keep_alive else "close"
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                try:
                    raw_resp = Serializer.serialize_response(resp)
                    sock.send_all(raw_resp)
                except (ConnectionError, TimeoutError):
                    break

                self._log_request(method, path, resp.status, duration_ms)

                if not keep_alive:
                    break

    def _log_request(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._log_lock:
            entry = LogEntry(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                method=method,
                path=path,
                status=status,
                duration_ms=duration_ms,
            )
            self.log_queue.put(entry)
            logger.info("%s %s -> %d (%.2f ms)", method, path, status, duration_ms)
