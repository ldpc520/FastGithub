"""日志页：实时日志流、自动滚动、清空。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from core.loghub import log
from ui.widgets import card
from ui.theme import FIELD_BG, FIELD_FG


class LogsPage(ttk.Frame):
    MAX_LINES = 3000

    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self._build_ui()
        self.service.log_signal.connect(self.on_log)
        for line in log.history():
            self._append(line)

    def _build_ui(self):
        head = ttk.Frame(self)
        head.pack(fill="x", pady=(0, 14))
        self.autoscroll = tk.BooleanVar(value=True)
        ttk.Checkbutton(head, text="自动滚动", variable=self.autoscroll).pack(side="right", padx=8)
        ttk.Button(head, text="清空", width=10, command=self._clear).pack(side="right")

        wrap, body = card(self)
        wrap.pack(fill="both", expand=True)
        self.text = tk.Text(body, wrap="none", height=20, bg=FIELD_BG, fg=FIELD_FG,
                            insertbackground=FIELD_FG, relief="flat", font=("Consolas", 10))
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)
        self.text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        # 日志级别着色
        self.text.tag_configure("INFO", foreground="#4a4a4a")
        self.text.tag_configure("DEBUG", foreground="#9a9a9a")
        self.text.tag_configure("WARN", foreground="#8A6100")
        self.text.tag_configure("ERROR", foreground="#C42B1C")

    def on_log(self, level, line):
        self._append(line, level)

    def _append(self, line, level=None):
        if level is None:
            level = "WARN" if "[WARN]" in line else "ERROR" if "[ERROR]" in line else "DEBUG" if "[DEBUG]" in line else "INFO"
        self.text.insert("end", line + "\n", level)
        # 限制行数
        if int(self.text.index("end-1c").split(".")[0]) > self.MAX_LINES:
            self.text.delete("1.0", "100.0")
        if self.autoscroll.get():
            self.text.see("end")

    def _clear(self):
        self.text.delete("1.0", "end")
        log.clear()
