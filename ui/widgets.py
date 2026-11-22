"""可复用 UI 控件（基于 tkwebui）：卡片、指标卡、表格、开关行、提示条。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from tkwebui import Card, PALETTE
from .theme import COLORS


def card(master, title: str | None = None, **kwargs) -> tuple[Card, ttk.Frame]:
    """返回 (卡片, 内容 frame)。用法：body = card(parent, '标题')[1]。"""
    wrap = Card(master, padding=14, **kwargs)
    body = ttk.Frame(wrap)
    body.pack(fill="both", expand=True)
    if title:
        ttk.Label(body, text=title, style="Strong.TLabel").pack(anchor="w", pady=(0, 10))
    return wrap, body


def metric_card(master, title: str, value: str = "-", accent: str | None = None) -> tuple[Card, ttk.Label]:
    """指标卡：标题 + 大号数值。"""
    wrap = Card(master, padding=14)
    ttk.Label(wrap, text=title, style="Muted.TLabel").pack(anchor="w")
    v = ttk.Label(wrap, text=value, style="Strong.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
    if accent:
        v.configure(foreground=accent)
    v.pack(anchor="w", pady=(6, 0))
    return wrap, v


def make_table(master, columns: list[tuple[str, str, int]], height: int = 10):
    """创建只读表格 + 滚动条。columns: [(id, 表头, 宽度), ...]，返回 (frame, tree)。"""
    frame = ttk.Frame(master)
    cols = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=cols, show="headings", height=height,
                        selectmode="browse")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    for cid, heading, width in columns:
        tree.heading(cid, text=heading, anchor="w")
        tree.column(cid, width=width, anchor="w", stretch=(cid == cols[-1]))
    # 交替行颜色
    tree.tag_configure("oddrow", background="#242038")
    return frame, tree


def toggle_row(master, title: str, description: str = "", checked: bool = False,
               on_change=None) -> tuple[ttk.Frame, tk.BooleanVar]:
    """开关行：左侧标题+描述，右侧开关。返回 (frame, BooleanVar)。"""
    row = ttk.Frame(master, padding=(6, 8))
    left = ttk.Frame(row)
    left.pack(side="left", fill="x", expand=True)
    ttk.Label(left, text=title).pack(anchor="w")
    if description:
        ttk.Label(left, text=description, style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
    var = tk.BooleanVar(value=checked)
    chk = ttk.Checkbutton(row, variable=var, command=on_change, text="")
    chk.pack(side="right")
    return row, var


def divider(master) -> ttk.Frame:
    """1px 分隔线。"""
    line = ttk.Frame(master, height=1, style="Sidebar.TFrame")
    line.pack(fill="x", pady=2)
    return line
