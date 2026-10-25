import json
import re
import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Dict


class HeaderTable(ttk.Frame):
    """Таблица заголовков запроса с кнопками добавления и удаления строк."""

    def __init__(self, parent):
        super().__init__(parent)
        cols = ("name", "value")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=4)
        self.tree.heading("name", text="Имя заголовка")
        self.tree.heading("value", text="Значение")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("value", width=320, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(btn_frame, text="+ Добавить", command=self.add_row).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="- Удалить", command=self.remove_selected).pack(fill=tk.X, pady=2)

    def add_row(self, name: str = "", value: str = "") -> None:
        if not name:
            name = simpledialog.askstring("Заголовок", "Имя заголовка:", parent=self) or ""
        if not name.strip():
            return
        if not value:
            value = simpledialog.askstring("Заголовок", f"Значение для '{name}':", parent=self) or ""
        self.tree.insert("", tk.END, values=(name.strip(), value.strip()))

    def remove_selected(self) -> None:
        for item in self.tree.selection():
            self.tree.delete(item)

    def clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for item in self.tree.get_children():
            k, v = self.tree.item(item, "values")
            if k:
                headers[str(k)] = str(v)
        return headers


class LogTable(ttk.Frame):
    """Таблица логов входящих запросов на вкладке Сервера."""

    def __init__(self, parent):
        super().__init__(parent)
        cols = ("time", "method", "path", "status", "duration")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self.tree.heading("time", text="Время")
        self.tree.heading("method", text="Метод")
        self.tree.heading("path", text="Путь")
        self.tree.heading("status", text="Статус")
        self.tree.heading("duration", text="Время (мс)")

        self.tree.column("time", width=100, anchor="center")
        self.tree.column("method", width=80, anchor="center")
        self.tree.column("path", width=280, anchor="w")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("duration", width=100, anchor="e")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def add_log(self, timestamp: str, method: str, path: str, status: int, duration_ms: float) -> None:
        self.tree.insert("", tk.END, values=(timestamp, method, path, status, f"{duration_ms:.2f}"))
        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])

    def clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)


def highlight_syntax(text_widget: tk.Text, content: str, content_type: str = "") -> None:
    """Форматирует и подсвечивает JSON и HTML в текстовом поле ответа."""
    text_widget.configure(state=tk.NORMAL)
    text_widget.delete("1.0", tk.END)

    text_widget.tag_configure("json_key", foreground="#0451a5")
    text_widget.tag_configure("json_str", foreground="#a31515")
    text_widget.tag_configure("html_tag", foreground="#800000")
    text_widget.tag_configure("error_text", foreground="#d32f2f", font=("Consolas", 10, "bold"))

    is_json = "json" in content_type.lower() or content.strip().startswith(("{", "["))
    if is_json:
        try:
            parsed = json.loads(content)
            content = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            pass

    text_widget.insert("1.0", content)

    if is_json:
        for match in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end() - 1}c"
            text_widget.tag_add("json_key", start, end)
    elif "html" in content_type.lower() or "<" in content:
        for match in re.finditer(r"</?[a-zA-Z0-9][^>]*>", content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            text_widget.tag_add("html_tag", start, end)