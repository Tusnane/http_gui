import tkinter as tk
from tkinter import ttk
from .client_tab import ClientTab
from .server_tab import ServerTab


class HttpGuiApp(tk.Tk):
    """Главное окно приложения в стиле Telegram Dark (темно-синяя тема)."""

    def __init__(self):
        super().__init__()
        self.title("HTTP-клиент и сервер на чистых сокетах (Telegram Dark)")
        self.geometry("960x720")
        self.minsize(800, 600)

        self.timeout_var = tk.IntVar(value=5000)

        # Настраиваем палитру в стиле Telegram Desktop Dark
        self.bg_main = "#17212b"       # Основной фон окна
        self.bg_card = "#242f3d"       # Фон панелей и полей
        self.fg_text = "#f5f5f5"       # Основной текст
        self.accent_color = "#5288c1"  # Брендовый синий Telegram
        self.accent_hover = "#406d9b"  # Цвет при наведении на кнопку

        self.configure(bg=self.bg_main)
        self._apply_telegram_styles()
        self._build_tabs()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _apply_telegram_styles(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Базовые настройки шрифтов и цветов для всех виджетов ttk
        self.style.configure(".", background=self.bg_main, foreground=self.fg_text, font=("Segoe UI", 10))
        
        # Настройка вкладок (Notebook)
        self.style.configure("TNotebook", background=self.bg_main, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.bg_card, foreground=self.fg_text, padding=[16, 8], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", 
                       background=[("selected", self.accent_color)], 
                       foreground=[("selected", "#ffffff")])

        # Фреймы и LabelFrame
        self.style.configure("TFrame", background=self.bg_main)
        self.style.configure("TLabelframe", background=self.bg_main, foreground=self.fg_text, bordercolor="#2b3b4e")
        self.style.configure("TLabelframe.Label", background=self.bg_main, foreground="#769fc0", font=("Segoe UI", 9, "bold"))

        # Кнопки в стиле Telegram
        self.style.configure("TButton", 
                             background=self.accent_color, 
                             foreground="#ffffff", 
                             borderwidth=0, 
                             focusthickness=0, 
                             padding=[12, 6], 
                             font=("Segoe UI", 9, "bold"))
        self.style.map("TButton", background=[("active", self.accent_hover), ("pressed", "#33557a")])

        # Комбобоксы и Поля ввода
        self.style.configure("TCombobox", fieldbackground=self.bg_card, selectbackground=self.accent_color)
        self.style.configure("TEntry", fieldbackground=self.bg_card)

        # Таблицы (Treeview)
        self.style.configure("Treeview", 
                             background=self.bg_card, 
                             foreground=self.fg_text, 
                             fieldbackground=self.bg_card, 
                             borderwidth=0,
                             rowheight=24)
        self.style.configure("Treeview.Heading", 
                             background="#1e2c3a", 
                             foreground="#8faed6", 
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", self.accent_color)], foreground=[("selected", "#ffffff")])

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.client_tab = ClientTab(notebook, get_timeout_ms=self.get_timeout)
        self.server_tab = ServerTab(notebook)
        self.settings_tab = self._build_settings_tab(notebook)

        notebook.add(self.client_tab, text="  🌐  HTTP-Клиент  ")
        notebook.add(self.server_tab, text="  🖥  HTTP-Сервер  ")
        notebook.add(self.settings_tab, text="  ⚙  Настройки  ")

    def _build_settings_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=24)

        title_lbl = ttk.Label(frame, text="Настройки приложения", font=("Segoe UI", 14, "bold"), foreground="#769fc0")
        title_lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        ttk.Label(frame, text="Таймаут по умолчанию (мс):").grid(row=1, column=0, sticky="w", pady=10)
        timeout_entry = ttk.Entry(frame, textvariable=self.timeout_var, width=14)
        timeout_entry.grid(row=1, column=1, sticky="w", padx=12, pady=10)

        info_lbl = ttk.Label(
            frame, 
            text="💡 Интерфейс работает в тёмно-синем стиле Telegram Dark.\nИстория запросов автоматически сохраняется в файл history.json.",
            foreground="#8c9fad"
        )
        info_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=20)

        return frame

    def get_timeout(self) -> int:
        try:
            val = int(self.timeout_var.get())
            return max(100, val)
        except (ValueError, tk.TclError):
            return 5000

    def on_close(self) -> None:
        self.server_tab.stop_server()
        self.destroy()