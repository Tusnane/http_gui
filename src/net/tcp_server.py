import socket
from .socket_wrapper import Socket


class TcpServer:
    """Низкоуровневый TCP-сервер (bind, listen, accept)."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, backlog: int = 128):
        self.host = host
        self.port = port
        self.backlog = backlog
        self._sock: socket.socket | None = None

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Позволяет сразу переиспользовать порт после остановки сервера (Вопрос №14)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(self.backlog)
        # Таймаут на accept, чтобы поток сервера мог периодически проверять флаг остановки (Вопрос №24)
        self._sock.settimeout(0.5)

    def accept(self) -> tuple[Socket, tuple[str, int]] | None:
        if self._sock is None:
            raise ConnectionError("Сервер не запущен")
        try:
            client_sock, addr = self._sock.accept()
            return Socket(client_sock), addr
        except socket.timeout:
            return None
        except OSError:
            return None

    def stop(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None
