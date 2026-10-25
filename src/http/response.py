from dataclasses import dataclass, field
from typing import Dict


STATUS_REASONS = {
    200: "OK",
    301: "Moved Permanently",
    302: "Found",
    307: "Temporary Redirect",
    400: "Bad Request",
    404: "Not Found",
    418: "I'm a teapot",
    500: "Internal Server Error",
}


@dataclass
class Response:
    status: int
    reason: str = ""
    version: str = "HTTP/1.1"
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def __post_init__(self):
        if not self.reason:
            self.reason = STATUS_REASONS.get(self.status, "Unknown")
