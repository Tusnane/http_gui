import socket
from src.http.parser import MAX_HEADER_SIZE
from src.http.url import ParseError


class Socket:
    """Контекстный менеджер для сокета (RAII)."""

    def __init__(self, sock: socket.socket):
        self._sock: socket.socket | None = sock

    def __enter__(self) -> "Socket":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False  # Не подавляем исключения (Вопрос №17)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None

    def settimeout(self, timeout: float | None) -> None:
        if self._sock is None:
            raise ConnectionError("Сокет закрыт")
        self._sock.settimeout(timeout)

    def send_all(self, data: bytes) -> None:
        if self._sock is None:
            raise ConnectionError("Сокет закрыт")
        try:
            self._sock.sendall(data)
        except socket.timeout as exc:
            raise TimeoutError("Таймаут при отправке данных") from exc
        except OSError as exc:
            raise ConnectionError(f"Ошибка отправки данных: {exc}") from exc

    def recv(self, n: int = 4096) -> bytes:
        if self._sock is None:
            raise ConnectionError("Сокет закрыт")
        try:
            return self._sock.recv(n)
        except socket.timeout as exc:
            raise TimeoutError("Таймаут ожидания данных (recv)") from exc
        except OSError as exc:
            raise ConnectionError(f"Ошибка чтения из сокета: {exc}") from exc

    def read_http_message(self) -> bytes:
        """Читает одно полное HTTP-сообщение (заголовки + тело) из сокета."""
        buffer = bytearray()
        while b"\r\n\r\n" not in buffer:
            chunk = self.recv(4096)
            if not chunk:
                if not buffer:
                    return b""
                raise ParseError("Соединение закрыто до окончания заголовков")
            buffer.extend(chunk)
            if len(buffer) > MAX_HEADER_SIZE + 65536:
                raise ParseError("Превышен лимит заголовков")

        sep_idx = buffer.find(b"\r\n\r\n")
        if sep_idx > MAX_HEADER_SIZE:
            raise ParseError("Превышен максимальный размер заголовков (8 КБ)")

        header_bytes = bytes(buffer[:sep_idx])
        body_start = sep_idx + 4

        header_text = header_bytes.decode("iso-8859-1", errors="replace")
        headers_lower = {}
        for line in header_text.split("\r\n")[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers_lower[k.strip().lower()] = v.strip()

        if "content-length" in headers_lower:
            try:
                content_length = int(headers_lower["content-length"])
            except ValueError as exc:
                raise ParseError("Некорректный Content-Length") from exc

            total_needed = body_start + content_length
            while len(buffer) < total_needed:
                chunk = self.recv(min(4096, total_needed - len(buffer)))
                if not chunk:
                    raise ParseError("Соединение разорвано до получения всего тела")
                buffer.extend(chunk)
            return bytes(buffer[:total_needed])

        if "transfer-encoding" in headers_lower and "chunked" in headers_lower["transfer-encoding"].lower():
            while not buffer.endswith(b"0\r\n\r\n"):
                chunk = self.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
            return bytes(buffer)

        return bytes(buffer)
