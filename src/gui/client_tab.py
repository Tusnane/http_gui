import json
import logging
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from src.client.http_client import HttpClient
from src.http.response import Response
from src.http.url import ParseError, HttpError
from .widgets import HeaderTable, highlight_syntax

logger = logging.getLogger("http_gui")
HISTORY_FILE = Path("history.json")


class ClientTab(ttk.Frame):
    """Вкладка HTTP-клиента."""

    def __init__(self, parent, get_timeout_ms: Callable[[], int]):
        super().__init__(parent, padding=10)
        self.get_timeout_ms = get_timeout_ms
        self.result_queue: queue.Queue = queue.Queue()
        self._build_ui()
        self._poll_queue()

    def _build_ui(self) -> None:
        # Верхняя панель: Метод, URL, Отправить, Очистить
        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top, text="Метод:").pack(side=tk.LEFT)
        self.method_var = tk.StringVar(value="GET")
        self.method_combo = ttk.Combobox(
            top, textvariable=self.method_var, values=["GET", "POST"], width=8, state="readonly"
        )
        self.method_combo.pack(side=tk.LEFT, padx=5)
        self.method_combo.bind("<<ComboboxSelected>>", self._on_method_change)

        ttk.Label(top, text="URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value="http://localhost:8080/")
        self.url_entry = ttk.Entry(top, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.send_btn = ttk.Button(top, text="Отправить", command=self.send_request)
        self.send_btn.pack(side=tk.LEFT, padx=3)

        self.clear_btn = ttk.Button(top, text="Очистить", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=3)

        self.spinner_var = tk.StringVar(value="Готов")
        self.spinner_lbl = ttk.Label(top, textvariable=self.spinner_var, width=16, anchor="e")
        self.spinner_lbl.pack(side=tk.RIGHT, padx=5)

        # Заголовки запроса
        hdr_box = ttk.LabelFrame(self, text="Заголовки запроса", padding=5)
        hdr_box.pack(fill=tk.X, pady=4)
        self.header_table = HeaderTable(hdr_box)
        self.header_table.pack(fill=tk.X)

        # Тело запроса (активно только для POST)
        body_box = ttk.LabelFrame(self, text="Тело запроса (активно только для POST)", padding=5)
        body_box.pack(fill=tk.X, pady=4)
        self.req_body_text = tk.Text(body_box, height=4, font=("Consolas", 10))
        self.req_body_text.pack(fill=tk.X)
        self._on_method_change()

        # Область ответа
        resp_box = ttk.LabelFrame(self, text="Ответ сервера", padding=5)
        resp_box.pack(fill=tk.BOTH, expand=True, pady=4)

        status_bar = ttk.Frame(resp_box)
        status_bar.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(status_bar, text="Статус:").pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="—")
        ttk.Label(status_bar, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(
            side=tk.LEFT, padx=8
        )

        paned = ttk.PanedWindow(resp_box, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        hdr_resp_frame = ttk.Frame(paned)
        ttk.Label(hdr_resp_frame, text="Заголовки ответа:").pack(anchor="w")
        self.resp_headers_text = tk.Text(hdr_resp_frame, height=5, font=("Consolas", 9))
        self.resp_headers_text.pack(fill=tk.BOTH, expand=True)
        paned.add(hdr_resp_frame, weight=1)

        body_resp_frame = ttk.Frame(paned)
        ttk.Label(body_resp_frame, text="Тело ответа (JSON / HTML / Текст):").pack(anchor="w")
        self.resp_body_text = tk.Text(body_resp_frame, height=10, font=("Consolas", 10))
        self.resp_body_text.pack(fill=tk.BOTH, expand=True)
        paned.add(body_resp_frame, weight=3)

    def _on_method_change(self, _event=None) -> None:
        if self.method_var.get() == "POST":
            self.req_body_text.configure(state=tk.NORMAL, background="white")
        else:
            self.req_body_text.configure(state=tk.DISABLED, background="#f0f0f0")

    def clear_all(self) -> None:
        self.url_var.set("")
        self.header_table.clear()
        self.req_body_text.configure(state=tk.NORMAL)
        self.req_body_text.delete("1.0", tk.END)
        self._on_method_change()
        self.status_var.set("—")
        self.resp_headers_text.delete("1.0", tk.END)
        self.resp_body_text.delete("1.0", tk.END)
        self.spinner_var.set("Готов")

    def send_request(self) -> None:
        url = self.url_var.get().strip()
        method = self.method_var.get().upper()
        headers = self.header_table.get_headers()
        body = ""
        if method == "POST":
            body = self.req_body_text.get("1.0", tk.END).rstrip("\n")

        self.send_btn.configure(state=tk.DISABLED)
        self.spinner_var.set("⏳ Отправка...")
        self.status_var.set("Ожидание...")

        timeout_ms = self.get_timeout_ms()
        thread = threading.Thread(
            target=self._worker_request,
            args=(method, url, headers, body, timeout_ms),
            daemon=True,
        )
        thread.start()

    def _worker_request(
        self, method: str, url: str, headers: dict, body: str, timeout_ms: int
    ) -> None:
        start_t = time.perf_counter()
        try:
            client = HttpClient(timeout_ms=timeout_ms)
            if method == "GET":
                resp = client.get(url, headers=headers)
            else:
                ct = headers.get("Content-Type", "text/plain; charset=utf-8")
                resp = client.post(url, body=body.encode("utf-8"), content_type=ct, headers=headers)
            elapsed = round((time.perf_counter() - start_t) * 1000, 2)
            self._save_history(method, url, resp.status, elapsed)
            self.result_queue.put(("ok", resp, elapsed))
        except (ParseError, ConnectionError, TimeoutError, HttpError, ValueError) as exc:
            logger.warning("Ошибка клиентского запроса (%s %s): %s", method, url, exc)
            self.result_queue.put(("error", f"{type(exc).__name__}: {exc}", 0.0))
        except Exception as exc:
            logger.exception("Непредвиденная ошибка клиента")
            self.result_queue.put(("error", f"Ошибка: {exc}", 0.0))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload, elapsed = self.result_queue.get_nowait()
                self.send_btn.configure(state=tk.NORMAL)
                if kind == "ok":
                    resp: Response = payload
                    self.spinner_var.set(f"Готово ({elapsed} мс)")
                    self.status_var.set(f"{resp.status} {resp.reason}")
                    hdr_lines = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
                    self.resp_headers_text.delete("1.0", tk.END)
                    self.resp_headers_text.insert("1.0", hdr_lines)

                    ct = ""
                    for k, v in resp.headers.items():
                        if k.lower() == "content-type":
                            ct = v
                            break
                    body_text = resp.body.decode("utf-8", errors="replace")
                    highlight_syntax(self.resp_body_text, body_text, ct)
                else:
                    self.spinner_var.set("Ошибка")
                    self.status_var.set("ОШИБКА")
                    self.resp_headers_text.delete("1.0", tk.END)
                    self.resp_body_text.delete("1.0", tk.END)
                    self.resp_body_text.insert("1.0", str(payload), "error_text")
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_queue)

    @staticmethod
    def _save_history(method: str, url: str, status: int, elapsed_ms: float) -> None:
        try:
            items = []
            if HISTORY_FILE.exists():
                items = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            items.append(
                {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "method": method,
                    "url": url,
                    "status": status,
                    "elapsed_ms": elapsed_ms,
                }
            )
            HISTORY_FILE.write_text(json.dumps(items[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
