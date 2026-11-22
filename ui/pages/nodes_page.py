"""节点测速页：github.akams.cn 节点聚合、测速排序、加速链接生成。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from core.nodes import NodeManager
from ui.widgets import card, make_table
from ui.theme import COLORS


class NodesPage(ttk.Frame):
    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self._build_ui()
        self.service.node_progress_signal.connect(self._on_progress)
        self.service.nodes_done_signal.connect(self._on_done)
        self.load_nodes()

    def _build_ui(self):
        head = ttk.Frame(self)
        head.pack(fill="x", pady=(0, 14))
        self.progress = ttk.Progressbar(head, mode="determinate", length=180)
        self.progress.pack(side="right", padx=8)
        self.test_btn = ttk.Button(head, text="⟳ 批量测速", width=14,
                                   style="Primary.TButton", command=self._test)
        self.test_btn.pack(side="right")

        # 链接生成
        gen_wrap, gen_body = card(self, "加速链接生成")
        gen_wrap.pack(fill="x", pady=(0, 14))
        row = ttk.Frame(gen_body)
        row.pack(fill="x")
        ttk.Label(row, text="GitHub 链接：").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_input = ttk.Entry(row, textvariable=self.url_var)
        self.url_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.node_var = tk.StringVar()
        self.node_combo = ttk.Combobox(row, textvariable=self.node_var, state="readonly", width=24)
        self.node_combo.pack(side="left", padx=(0, 8))
        ttk.Button(row, text="生成", width=8, command=self._generate).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="复制结果", width=10, command=self._copy).pack(side="left")

        self.result_label = ttk.Label(gen_body, text="生成的加速链接会显示在这里",
                                      style="Muted.TLabel", wraplength=900, justify="left")
        self.result_label.pack(anchor="w", pady=(10, 0))
        self._result = ""

        # 节点表
        table_wrap, table_body = card(self, "公开节点列表（来自 github.akams.cn，风语轮迹置顶）")
        table_wrap.pack(fill="both", expand=True)
        self.table_frame, self.table = make_table(
            table_body,
            [("name", "节点", 220), ("status", "状态", 90),
             ("latency", "延迟(ms)", 90), ("url", "地址", 420)],
            height=12,
        )
        self.table_frame.pack(fill="both", expand=True)

    def _test(self):
        self.test_btn.configure(state="disabled", text="测速中…")
        self.progress.pack(side="right", padx=8)
        self.progress.configure(value=0, maximum=len(self.service.nodemgr.results))
        self.service.test_nodes()

    def _on_progress(self, done, total):
        self.progress.configure(value=done, maximum=max(1, total))

    def _on_done(self, results):
        self.test_btn.configure(state="normal", text="⟳ 批量测速")
        self.progress.pack_forget()
        self.load_nodes(results)

    def load_nodes(self, results=None):
        results = results or self.service.nodemgr.results
        for row in self.table.get_children():
            self.table.delete(row)
        for idx, node in enumerate(results):
            status = "✓ 可用" if node.ok else "✗ 不可用"
            lat = str(int(node.latency_ms)) if node.ok else "-"
            tag = ("ok",) if node.ok else ("bad",)
            if idx % 2:
                tag = tag + ("oddrow",)
            self.table.insert("", "end", values=(node.name, status, lat, node.url), tags=tag)
        self.table.tag_configure("ok", foreground=COLORS["green"])
        self.table.tag_configure("bad", foreground=COLORS["red"])

        # 下拉框：可用节点优先，风语轮迹置顶（结果已按置顶+延迟排序）
        current = self.node_combo.get()
        display = [n for n in results if n.ok] or results
        labels = []
        self._combo_urls = {}
        for n in display:
            label = f"{n.name} ({int(n.latency_ms)}ms)" if n.ok and n.latency_ms >= 0 else n.name
            labels.append(label)
            self._combo_urls[label] = n.url
        self.node_combo["values"] = labels
        if labels:
            # 尽量保留上次选择
            restore = next((l for l in labels if current and current.split(" (")[0] == l.split(" (")[0]), labels[0])
            self.node_combo.set(restore)

    def _generate(self):
        url = self.url_var.get().strip()
        label = self.node_var.get()
        node_url = self._combo_urls.get(label, "")
        if not url or not node_url:
            self.result_label.configure(text="请先输入 GitHub 链接并选择节点", style="Danger.TLabel")
            self._result = ""
            return
        result = NodeManager.build_url(node_url, url)
        self._result = result
        self.result_label.configure(text=result, style="Link.TLabel")

    def _copy(self):
        if not self._result:
            messagebox.showinfo("提示", "还没有生成加速链接", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(self._result)
        self.update()
        messagebox.showinfo("已复制", "加速链接已复制到剪贴板", parent=self)
