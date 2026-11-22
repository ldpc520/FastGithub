"""Win11 浅色主题：覆盖 tkwebui 调色板为 Fluent 风格浅色。

在 root = tk.Tk() 之后、创建任何控件之前调用 apply_dark_theme(root)。
（函数名保留历史命名以兼容入口，实际套用的是 Win11 浅色风格。）
tkwebui 的 apply_theme 会读取模块级 PALETTE 字典，覆盖它即可
让 Card / Sidebar / 表格 / 按钮 / 输入框等全部组件换成浅色。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from tkwebui import PALETTE, apply_theme as _tkwebui_apply

# Win11 Fluent 浅色风格
LIGHT = {
    "bg": "#FFFFFF",          # 主背景
    "sidebar": "#F3F3F3",     # 侧栏背景
    "fg": "#1B1B1B",          # 主文字
    "muted": "#616161",       # 次要文字
    "border": "#E5E5E5",      # 边框
    "hover": "#EEEEEE",       # 悬停
    "active": "#E0E0E0",      # 选中/激活
    "accent": "#0067C0",      # 强调色（Win11 蓝）
    "accent_hover": "#005A9E",
    "blue": "#0067C0",
    "selected": "#E8F0FE",    # 选中行/卡片
    "disabled": "#9A9A9A",
}

# 兼容旧导入名（main_window.py 仍 from ui.theme import DARK）
DARK = LIGHT

# 语义色（浅底上加深以保证对比度）
COLORS = {
    "green": "#107C10",      # Win11 绿
    "red": "#C42B1C",        # Win11 红
    "blue": "#0067C0",       # Win11 蓝
    "purple": "#6B46C1",     # 深紫（浅底可读）
    "yellow": "#8A6100",     # 深黄（浅底文字可读）
}

# 提示条 / 文本框背景
NOTICE_BG = "#FFF4CE"        # Win11 浅黄提示底
FIELD_BG = "#FFFFFF"         # 输入框底
FIELD_FG = "#1B1B1B"         # 输入框文字
PLACEHOLDER_FG = "#9A9A9A"   # 占位符
CHART_BG = "#FAFAFA"         # 流量图背景
GRID = "#E5E5E5"             # 图表网格
ALT_ROW = "#F5F5F7"          # 表格交替行


def apply_dark_theme(root: tk.Tk) -> dict:
    """覆盖调色板并应用 tkwebui 主题，返回调色板副本。"""
    PALETTE.update(LIGHT)
    palette = _tkwebui_apply(
        root,
        font_family="Microsoft YaHei UI",
        font_size=10,
        accent=LIGHT["accent"],
        accent_hover=LIGHT["accent_hover"],
    )
    # 补充自定义样式：状态标签、提示条等
    style = ttk.Style(root)
    style.configure("Success.TLabel", foreground=COLORS["green"], background=LIGHT["bg"])
    style.configure("Danger.TLabel", foreground=COLORS["red"], background=LIGHT["bg"])
    style.configure("StatusOn.TLabel", foreground=COLORS["green"], background=LIGHT["bg"])
    style.configure("StatusOff.TLabel", foreground=COLORS["red"], background=LIGHT["bg"])
    style.configure("Warn.TLabel", foreground=COLORS["yellow"], background=NOTICE_BG)
    style.configure("Link.TLabel", foreground=COLORS["blue"], background=LIGHT["bg"])
    # 提示条：浅黄底深黄字（Win11 通知风格）
    style.configure("Notice.TFrame", background=NOTICE_BG)
    return palette
