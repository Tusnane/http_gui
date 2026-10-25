import socket
import ssl
from .socket_wrapper import Socket


class TcpClient:
    """TCP-клиент с поддержкой таймаута и SSL (HTTPS)."""

    @staticmethod
    def connect(host: str, port: int, timeout_ms: int = 5000, use_ssl: bool = False) -> Socket:
        timeout_sec = timeout_ms / 1000.0
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(timeout_sec)
        try:
            raw_sock.connect((host, port))
            if use_ssl:
                context = ssl.create_default_context()
                raw_sock = context.wrap_socket(raw_sock, server_hostname=host)
                raw_sock.settimeout(timeout_sec)
            return Socket(raw_sock)
        except socket.timeout as exc:
            raw_sock.close()
            raise TimeoutError(f"Превышен таймаут подключения ({timeout_ms} мс) к {host}:{port}") from exc
        except OSError as exc:
            raw_sock.close()
            raise ConnectionError(f"Не удалось подключиться к {host}:{port}: {exc}") from exc
