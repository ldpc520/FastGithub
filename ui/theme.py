"""暗色主题：把 tkwebui 的浅色调色板覆盖为深紫黑风格。

在 root = tk.Tk() 之后、创建任何控件之前调用 apply_dark_theme(root)。
tkwebui 的 apply_theme 会读取模块级 PALETTE 字典，因此覆盖它即可
让 Card / Sidebar / 表格 / 按钮 / 输入框等全部组件换成暗色。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from tkwebui import PALETTE, apply_theme as _tkwebui_apply

# 深紫黑风格（沿用原 PyQt6 版本配色，用户已确认喜欢）
DARK = {
    "bg": "#1e1b2e",          # 主背景
    "sidebar": "#211e33",     # 侧栏背景
    "fg": "#d5d3e8",          # 主文字
    "muted": "#8b86a8",       # 次要文字
    "border": "#322d4a",      # 边框
    "hover": "#292541",       # 悬停
    "active": "#3a3358",      # 选中/激活
    "accent": "#7c5cff",      # 强调色（紫）
    "accent_hover": "#6a4ce0",
    "blue": "#8b7bff",
    "selected": "#332c55",    # 选中行/卡片
    "disabled": "#5a5670",
}

# 附加语义色（图表曲线、状态）
COLORS = {
    "green": "#4ec9a0",
    "red": "#e06c75",
    "blue": "#7f9dff",
    "purple": "#a792ff",
    "yellow": "#e8c05a",
}


def apply_dark_theme(root: tk.Tk) -> dict:
    """覆盖调色板并应用 tkwebui 主题，返回调色板副本。"""
    PALETTE.update(DARK)
    palette = _tkwebui_apply(
        root,
        font_family="Microsoft YaHei UI",
        font_size=10,
        accent=DARK["accent"],
        accent_hover=DARK["accent_hover"],
    )
    # 补充自定义样式：状态标签、提示条等
    style = ttk.Style(root)
    style.configure("Success.TLabel", foreground=COLORS["green"], background=DARK["bg"])
    style.configure("Danger.TLabel", foreground=COLORS["red"], background=DARK["bg"])
    style.configure("StatusOn.TLabel", foreground=COLORS["green"], background=DARK["bg"])
    style.configure("StatusOff.TLabel", foreground=COLORS["red"], background=DARK["bg"])
    style.configure("Warn.TLabel", foreground=COLORS["yellow"], background=DARK["bg"])
    style.configure("Link.TLabel", foreground=COLORS["blue"], background=DARK["bg"])
    # 提示条：浅黄底深黄字，用 Quiet 框架背景近似
    style.configure("Notice.TFrame", background="#3a3320")
    return palette
