"""GitHub 直链转换页：blob 文件页链接 → raw 直链，支持批量、加速代理、实时转换。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.directlink import convert_batch
from ui.widgets import card


class DirectLinkPage(ttk.Frame):
    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self._build_ui()
        self.service.nodes_done_signal.connect(self._on_nodes_done)

    def _build_ui(self):
        # 输入区
        in_wrap, in_body = card(self, "粘贴 GitHub 链接（支持多行批量，每行一个）")
        in_wrap.pack(fill="both", expand=True, pady=(0, 14))
        self.input = tk.Text(in_body, height=6, wrap="none", bg="#151822", fg="#d5d3e8",
                             insertbackground="#d5d3e8", relief="flat", font=("Microsoft YaHei UI", 10))
        self.input.pack(fill="both", expand=True)
        self._set_placeholder()
        self.input.bind("<FocusIn>", self._on_focus_in)
        self.input.bind("<FocusOut>", self._on_focus_out)
        self.input.bind("<KeyRelease>", lambda e: self._convert())

        opt = ttk.Frame(in_body)
        opt.pack(fill="x", pady=(10, 0))
        ttk.Label(opt, text="加速代理：").pack(side="left")
        self.proxy_var = tk.StringVar()
        self.proxy_combo = ttk.Combobox(opt, textvariable=self.proxy_var, state="readonly", width=42)
        self.proxy_combo.pack(side="left", padx=(0, 8))
        self.proxy_combo.bind("<<ComboboxSelected>>", lambda e: self._convert())
        ttk.Button(opt, text="转换", style="Primary.TButton", command=self._convert).pack(side="left", padx=(0, 6))
        ttk.Button(opt, text="清空", command=self._clear).pack(side="left", padx=(0, 6))
        self.copy_btn = ttk.Button(opt, text="复制全部", command=self._copy_all)
        self.copy_btn.pack(side="left")

        # 输出区
        out_wrap, out_body = card(self, "转换结果")
        out_wrap.pack(fill="both", expand=True)
        ttk.Label(out_body, text="blob/raw 文件页 → raw 直链；tree 目录页 → zip 打包下载；每行一个，实时转换。",
                  style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
        self.output = tk.Text(out_body, height=8, wrap="none", bg="#151822", fg="#7f9dff",
                              insertbackground="#d5d3e8", relief="flat", font=("Microsoft YaHei UI", 10))
        vsb = ttk.Scrollbar(out_body, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=vsb.set)
        self.output.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # 输出控件就绪后再填充下拉（会触发 _convert）
        self._fill_proxy_combo()

    def _set_placeholder(self):
        self.input.delete("1.0", "end")
        self.input.insert("1.0",
            "https://github.com/owner/repo/blob/main/path/to/file.txt\n"
            "https://github.com/owner/repo/tree/main/src")
        self.input.configure(fg="#6f7690")
        self._placeholder = True

    def _on_focus_in(self, event):
        if getattr(self, "_placeholder", False):
            self.input.delete("1.0", "end")
            self.input.configure(fg="#d5d3e8")
            self._placeholder = False

    def _on_focus_out(self, event):
        if not self.input.get("1.0", "end").strip():
            self._set_placeholder()

    def _fill_proxy_combo(self, keep=None):
        current = keep or self.proxy_var.get()
        labels = ["不使用（生成原始直链）"]
        self._proxy_urls = {"不使用（生成原始直链）": ""}
        for node in self.service.nodemgr.results:
            label = node.name
            if node.ok and node.latency_ms >= 0:
                label += f"  ·  {node.latency_ms:.0f}ms"
            labels.append(label)
            self._proxy_urls[label] = node.url
        self.proxy_combo["values"] = labels
        if current in labels:
            self.proxy_var.set(current)
        else:
            self.proxy_var.set(labels[0])
        self._convert()

    def _on_nodes_done(self, results):
        self._fill_proxy_combo(keep=self.proxy_var.get())

    def _input_text(self):
        if getattr(self, "_placeholder", False):
            return ""
        return self.input.get("1.0", "end")

    def _convert(self):
        proxy = self._proxy_urls.get(self.proxy_var.get(), "")
        result = convert_batch(self._input_text(), proxy)
        self.output.delete("1.0", "end")
        if result:
            self.output.insert("1.0", result)

    def _clear(self):
        self.input.delete("1.0", "end")
        self._placeholder = False
        self.output.delete("1.0", "end")

    def _copy_all(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.copy_btn.configure(text="已复制 ✓")
        self.after(1500, lambda: self.copy_btn.configure(text="复制全部"))
