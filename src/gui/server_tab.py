import queue
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from src.server.http_server import HttpServer, LogEntry
from .widgets import LogTable


class ServerTab(ttk.Frame):
    """Вкладка управления HTTP-сервером и просмотра логов."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.log_queue: queue.Queue = queue.Queue()
        self.server: HttpServer | None = None
        self._build_ui()
        self._poll_logs()

    def _build_ui(self) -> None:
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ctrl, text="Порт:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="8080")
        self.port_entry = ttk.Entry(ctrl, textvariable=self.port_var, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(ctrl, text="Запустить", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=3)

        self.stop_btn = ttk.Button(ctrl, text="Остановить", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)

        # Индикатор состояния (зелёный / красный кружок)
        self.status_canvas = tk.Canvas(ctrl, width=18, height=18, highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT, padx=(12, 4))
        self.indicator = self.status_canvas.create_oval(2, 2, 16, 16, fill="#d32f2f", outline="")

        self.state_lbl_var = tk.StringVar(value="Остановлен")
        ttk.Label(ctrl, textvariable=self.state_lbl_var, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        ttk.Button(ctrl, text="Открыть в браузере", command=self.open_browser).pack(side=tk.RIGHT, padx=3)
        ttk.Button(ctrl, text="Очистить лог", command=self.clear_logs).pack(side=tk.RIGHT, padx=3)

        log_box = ttk.LabelFrame(self, text="Лог входящих HTTP-запросов", padding=5)
        log_box.pack(fill=tk.BOTH, expand=True)

        self.log_table = LogTable(log_box)
        self.log_table.pack(fill=tk.BOTH, expand=True)

    def start_server(self) -> None:
        port_str = self.port_var.get().strip()
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка валидации", "Порт должен быть целым числом от 1 до 65535.")
            return

        try:
            self.server = HttpServer(host="127.0.0.1", port=port, log_queue=self.log_queue)
            self.server.start()
        except Exception as exc:
            messagebox.showerror("Ошибка запуска сервера", f"Не удалось запустить сервер:\n{exc}")
            self.server = None
            return

        self.status_canvas.itemconfig(self.indicator, fill="#388e3c")
        self.state_lbl_var.set(f"Работает (порт {port})")
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.port_entry.configure(state=tk.DISABLED)

    def stop_server(self) -> None:
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.status_canvas.itemconfig(self.indicator, fill="#d32f2f")
        self.state_lbl_var.set("Остановлен")
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.port_entry.configure(state=tk.NORMAL)

    def clear_logs(self) -> None:
        self.log_table.clear()

    def open_browser(self) -> None:
        port = self.port_var.get().strip() or "8080"
        webbrowser.open(f"http://localhost:{port}/")

    def _poll_logs(self) -> None:
        try:
            while True:
                entry: LogEntry = self.log_queue.get_nowait()
                self.log_table.add_log(
                    entry.timestamp, entry.method, entry.path, entry.status, entry.duration_ms
                )
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_logs)
