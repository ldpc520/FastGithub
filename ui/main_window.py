"""主窗口：左侧导航 + 页面切换 + 顶部标题栏/提示条 + 系统托盘。"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk

from core.loghub import log
from ui.theme import DARK, COLORS, NOTICE_BG
from ui.pages.dashboard import DashboardPage
from ui.pages.nodes_page import NodesPage
from ui.pages.releases_page import ReleasesPage
from ui.pages.directlink_page import DirectLinkPage
from ui.pages.logs_page import LogsPage
from ui.pages.settings_page import SettingsPage


def _resource(name: str) -> str:
    """兼容源码运行与 PyInstaller 打包后的资源路径。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", name)


class MainWindow:
    # (key, 显示名, tkwebui 内置图标名, 页面类, 标题, 副标题)
    PAGES = [
        ("dashboard", "总览", "speed", DashboardPage,
         "加速总览", "一键启停本地代理，查看流量统计与域名 IP 优选结果"),
        ("nodes", "加速节点", "sources", NodesPage,
         "GitHub 加速节点", "github.akams.cn 公开节点测速，一键生成加速下载链接"),
        ("releases", "Releases", "download", ReleasesPage,
         "Releases 加速下载", "查询仓库发布列表，右键资源用节点加速下载"),
        ("directlink", "直链转换", "edit", DirectLinkPage,
         "GitHub 直链转换", "把文件页链接转成 raw 直链，支持批量与加速代理"),
        ("logs", "日志", "library", LogsPage,
         "运行日志", "实时日志流，排障与状态追踪"),
        ("settings", "设置", "settings", SettingsPage,
         "设置", "启动、代理、IP 更新与目录诊断"),
    ]

    def __init__(self, root: tk.Tk, service):
        self.root = root
        self.service = service
        self._tray = None
        self._quitting = False
        self._build_ui()
        self._build_tray()
        # 定时把 core 线程的信号派发到 UI 主线程
        self._pump()

    # ---------- 构建 ----------
    def _build_ui(self):
        root = self.root
        root.title("FastGithubPy - GitHub 加速工具箱")
        root.geometry("1080x740")
        root.minsize(920, 640)
        ico = _resource("app.ico")
        if os.path.exists(ico):
            try:
                root.iconbitmap(ico)
            except Exception:
                pass

        main = ttk.Frame(root)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # 左侧导航（手动按钮，便于控制文字与配色）
        sidebar = ttk.Frame(main, width=190, style="Sidebar.TFrame")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="FastGithubPy", style="Strong.TLabel",
                  font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=16, pady=(18, 0))
        ttk.Label(sidebar, text="GitHub 加速工具箱", style="Muted.TLabel").pack(anchor="w", padx=16)
        ttk.Frame(sidebar, height=1, style="Sidebar.TFrame").pack(fill="x", padx=12, pady=14)

        self.nav_buttons: dict[str, ttk.Button] = {}
        self.nav_key_to_btn: dict[str, ttk.Button] = {}
        for key, label, _icon, _cls, _t, _s in self.PAGES:
            b = ttk.Button(sidebar, text=f"  {label}", style="Nav.TButton",
                           command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = b
        ttk.Label(sidebar, text="v1.0", style="Muted.TLabel").pack(side="bottom", pady=12)

        # 右侧内容区
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        # 顶部标题 + 副标题
        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))
        self.header_title = ttk.Label(header, text="加速总览", style="Strong.TLabel",
                                      font=("Microsoft YaHei UI", 17, "bold"))
        self.header_title.pack(anchor="w")
        self.header_sub = ttk.Label(header, text="一键启停本地代理，查看流量统计与域名 IP 优选结果",
                                    style="Muted.TLabel")
        self.header_sub.pack(anchor="w", pady=(3, 0))

        # 黄色提示条
        notice = ttk.Frame(right, padding=(12, 8), style="Notice.TFrame")
        notice.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        ttk.Label(notice, text="⚠", foreground=COLORS["yellow"],
                  background=NOTICE_BG, font=("Microsoft YaHei UI", 14)).pack(side="left")
        ttk.Label(notice, style="Warn.TLabel", background=NOTICE_BG,
                  text="首次使用请点「更新 IP」测速，再点「启动加速」；程序会自动设置/还原系统代理。",
                  wraplength=780, justify="left").pack(side="left", padx=8)

        # 页面容器
        self.pages: dict[str, tk.Widget] = {}
        self.container = ttk.Frame(right)
        self.container.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)
        for key, _label, _icon, cls, _t, _s in self.PAGES:
            page = cls(self.service, master=self.container)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page

        self.service.proxy_state_signal.connect(self._on_proxy_state)
        self.show_page(self.PAGES[0][0])

        # 关闭按钮 → 隐藏到托盘
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def show_page(self, key: str):
        page = self.pages.get(key)
        if not page:
            return
        page.tkraise()
        for item in self.PAGES:
            k = item[0]
            self.nav_buttons[k].configure(style="Selected.Nav.TButton" if k == key else "Nav.TButton")
        for item in self.PAGES:
            if item[0] == key:
                self.header_title.configure(text=item[4])
                self.header_sub.configure(text=item[5])
                break
        # 切到设置页时刷新系统代理状态（避免显示过期）
        refresher = getattr(page, "refresh_sysproxy_status", None)
        if refresher:
            refresher()

    # ---------- 托盘 ----------
    def _build_tray(self):
        try:
            from ui.tray import TrayController
            self._tray = TrayController(self)
            self._tray.start()
        except Exception as exc:
            log.warn(f"系统托盘不可用（不影响主界面）：{exc}")
            self._tray = None

    def toggle_proxy(self):
        if self.service.proxy.running:
            self.service.stop_proxy()
        else:
            self.service.start_proxy()

    def _on_proxy_state(self, running, port):
        if self._tray:
            self._tray.update_state(running, port)
        if self.service.cfg.get("tray_notify", True) and self._tray:
            self._tray.notify(
                "FastGithubPy",
                f"加速服务已{'启动' if running else '停止'}" + (f"（端口 {port}）" if running else ""),
            )

    def show_window(self):
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        """真正退出程序：移除托盘图标 → 关闭服务 → 销毁窗口。"""
        if self._quitting:
            return
        self._quitting = True
        try:
            if self._tray:
                self._tray.stop()  # 会等待托盘线程结束并注销图标
        except Exception:
            pass
        try:
            self.service.shutdown()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_close(self):
        # 关闭窗口 = 直接退出（避免"点了关闭却退不出"的困惑）
        self.quit_app()

    # ---------- 信号泵 ----------
    def _pump(self):
        self.service.pump_all(limit=300)
        self.root.after(50, self._pump)
