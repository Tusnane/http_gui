import tkinter as tk
from tkinter import ttk
from .client_tab import ClientTab
from .server_tab import ServerTab


class HttpGuiApp(tk.Tk):
    """Главное окно приложения с вкладками Клиент, Сервер и Настройки."""

    def __init__(self):
        super().__init__()
        self.title("HTTP-клиент и сервер на чистых сокетах (Python)")
        self.geometry("920x700")
        self.minsize(780, 580)

        self.timeout_var = tk.IntVar(value=5000)
        self.theme_var = tk.StringVar(value="light")

        self.style = ttk.Style(self)
        self._build_tabs()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.client_tab = ClientTab(notebook, get_timeout_ms=self.get_timeout)
        self.server_tab = ServerTab(notebook)
        self.settings_tab = self._build_settings_tab(notebook)

        notebook.add(self.client_tab, text="  🌐 HTTP-Клиент  ")
        notebook.add(self.server_tab, text="  🖥 HTTP-Сервер  ")
        notebook.add(self.settings_tab, text="  ⚙ Настройки  ")

    def _build_settings_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=20)

        ttk.Label(frame, text="Таймаут по умолчанию (мс):").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.timeout_var, width=12).grid(row=0, column=1, sticky="w", padx=10)

        ttk.Label(frame, text="Тема оформления:").grid(row=1, column=0, sticky="w", pady=8)
        theme_combo = ttk.Combobox(
            frame, textvariable=self.theme_var, values=["light", "dark"], state="readonly", width=10
        )
        theme_combo.grid(row=1, column=1, sticky="w", padx=10)
        theme_combo.bind("<<ComboboxSelected>>", self._apply_theme)

        ttk.Label(
            frame,
            text="История запросов автоматически сохраняется в файл history.json в папке проекта.",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

        return frame

    def _apply_theme(self, _event=None) -> None:
        if self.theme_var.get() == "dark":
            self.configure(bg="#2b2b2b")
            self.style.theme_use("clam")
            self.style.configure(".", background="#2b2b2b", foreground="#ffffff", fieldbackground="#3c3f41")
            self.style.configure("Treeview", background="#3c3f41", foreground="#ffffff", fieldbackground="#3c3f41")
        else:
            self.configure(bg="#f0f0f0")
            self.style.theme_use("vista" if "vista" in self.style.theme_names() else "default")
            self.style.configure(".", background="#f0f0f0", foreground="#000000", fieldbackground="#ffffff")
            self.style.configure("Treeview", background="#ffffff", foreground="#000000", fieldbackground="#ffffff")

    def get_timeout(self) -> int:
        try:
            val = int(self.timeout_var.get())
            return max(100, val)
        except (ValueError, tk.TclError):
            return 5000

    def on_close(self) -> None:
        """Корректная остановка фонового сервера при закрытии окна."""
        self.server_tab.stop_server()
        self.destroy()
