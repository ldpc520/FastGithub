"""设置页：加速配置、开机自启、托盘、自动刷新、代理模式、目录入口。"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from core import systemproxy
from core.config import CONFIG_DIR, IP_CACHE_FILE, LOG_DIR, LOG_FILE
from ui.widgets import card, toggle_row, divider


class SettingsPage(ttk.Frame):
    INTERVAL_CHOICES = [
        ("不自动更新", 0),
        ("15 分钟", 0.25),
        ("30 分钟", 0.5),
        ("1 小时", 1),
        ("2 小时", 2),
        ("6 小时", 6),
        ("12 小时", 12),
        ("24 小时", 24),
        ("3 天", 72),
    ]

    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self.cfg = service.cfg
        self._build_ui()
        self._load()
        self.service.proxy_state_signal.connect(self._on_proxy_state)

    def _build_ui(self):
        head = ttk.Frame(self)
        head.pack(fill="x", pady=(0, 14))
        ttk.Button(head, text="保存设置", style="Primary.TButton", command=self._save).pack(side="right")
        ttk.Label(head, text="设置", style="Strong.TLabel",
                  font=("Microsoft YaHei UI", 14, "bold")).pack(side="left")

        # 启动与运行
        run_wrap, run_body = card(self, "启动与运行")
        run_wrap.pack(fill="x", pady=(0, 14))
        self.autostart_row, self.autostart_var = toggle_row(
            run_body, "开机自启", "登录 Windows 后自动启动并加速",
            on_change=lambda: self.service.set_auto_start(self.autostart_var.get()))
        self.autostart_row.pack(fill="x")
        divider(run_body)
        self.mintray_row, self.mintray_var = toggle_row(
            run_body, "启动后最小化到托盘", "只在托盘显示图标，点击托盘恢复窗口")
        self.mintray_row.pack(fill="x")
        divider(run_body)
        self.autorefresh_row, self.autorefresh_var = toggle_row(
            run_body, "启动后检查 IP 缓存", "启动约 15 秒后检查缓存，有效则直接用，过期/缺失才测速")
        self.autorefresh_row.pack(fill="x")

        # 代理设置
        proxy_wrap, proxy_body = card(self, "代理设置")
        proxy_wrap.pack(fill="x", pady=(0, 14))
        mode_row = ttk.Frame(proxy_body)
        mode_row.pack(fill="x")
        ttk.Label(mode_row, text="代理模式：").pack(side="left")
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(mode_row, textvariable=self.mode_var, state="readonly", width=44)
        self.mode_combo["values"] = [
            "PAC 自动代理（仅 GitHub 走代理，推荐）",
            "全局代理（所有网站走代理）",
            "不修改系统设置（手动配置）",
        ]
        self.mode_combo.pack(side="left")
        ttk.Label(proxy_body, text="PAC 模式只加速 GitHub，其它网站不受影响，程序未运行时也不会断网",
                  style="Muted.TLabel", wraplength=800).pack(anchor="w", pady=(6, 10))
        port_row = ttk.Frame(proxy_body)
        port_row.pack(fill="x")
        ttk.Label(port_row, text="本地代理端口：").pack(side="left")
        self.port_var = tk.IntVar()
        self.port_spin = ttk.Spinbox(port_row, from_=1024, to=65535, textvariable=self.port_var, width=8)
        self.port_spin.pack(side="left", padx=(0, 8))
        ttk.Label(port_row, text="（修改后需重启加速生效）", style="Muted.TLabel").pack(side="left")

        sys_row = ttk.Frame(proxy_body)
        sys_row.pack(fill="x", pady=(12, 0))
        ttk.Label(sys_row, text="系统代理状态：").pack(side="left")
        self.sysproxy_value = ttk.Label(sys_row, text="-", style="Muted.TLabel")
        self.sysproxy_value.pack(side="left", padx=(6, 0))
        self.sysproxy_btn = ttk.Button(sys_row, text="开启", width=8, command=self._toggle_sysproxy)
        self.sysproxy_btn.pack(side="right")

        # IP 更新
        ip_wrap, ip_body = card(self, "IP 更新")
        ip_wrap.pack(fill="x", pady=(0, 14))
        int_row = ttk.Frame(ip_body)
        int_row.pack(fill="x")
        ttk.Label(int_row, text="自动更新间隔：").pack(side="left")
        self.interval_var = tk.StringVar()
        self.interval_combo = ttk.Combobox(int_row, textvariable=self.interval_var, state="readonly", width=16)
        self.interval_combo["values"] = [label for label, _ in self.INTERVAL_CHOICES]
        self.interval_combo.pack(side="left")
        ttk.Label(int_row, text="（缓存过期后自动测速，修改后需重启生效）",
                  style="Muted.TLabel").pack(side="left", padx=(8, 0))
        host_row = ttk.Frame(ip_body)
        host_row.pack(fill="x", pady=(10, 0))
        ttk.Label(host_row, text="hosts 源：").pack(side="left")
        self.hosts_var = tk.StringVar()
        ttk.Entry(host_row, textvariable=self.hosts_var, width=58).pack(side="left", fill="x", expand=True)

        # 目录
        dir_wrap, dir_body = card(self, "目录与诊断")
        dir_wrap.pack(fill="x")
        btn_row = ttk.Frame(dir_body)
        btn_row.pack(fill="x")
        for name, path in [("配置目录", CONFIG_DIR), ("日志目录", LOG_DIR), ("IP 缓存", IP_CACHE_FILE)]:
            ttk.Button(btn_row, text=f"打开{name}",
                       command=lambda p=path: self._open_path(p)).pack(side="left", padx=(0, 8))

    def _load(self):
        self.autostart_var.set(bool(self.cfg.get("auto_start", False)))
        self.mintray_var.set(bool(self.cfg.get("minimize_to_tray", True)))
        self.autorefresh_var.set(bool(self.cfg.get("auto_start_refresh", True)))
        self.port_var.set(int(self.cfg.get("proxy_port", 38457)))
        self.hosts_var.set(self.cfg.get("hosts_source", ""))
        mode = self.cfg.get("proxy_mode", "pac")
        idx = {"pac": 0, "global": 1, "off": 2}.get(mode, 0)
        self.mode_combo.current(idx)
        hours = float(self.cfg.get("auto_update_hours", 0) or 0)
        idx = next((i for i, (_, h) in enumerate(self.INTERVAL_CHOICES) if abs(h - hours) < 1e-6), 0)
        self.interval_combo.current(idx)
        self.refresh_sysproxy_status()

    def refresh_sysproxy_status(self):
        try:
            mode = systemproxy.get_proxy_mode()
        except Exception:
            mode = "off"
        label = {"pac": "PAC 自动代理", "global": "全局代理", "off": "未启用"}.get(mode, "未知")
        detail = ""
        if mode == "global":
            try:
                detail = systemproxy.get_system_proxy().get("server", "")
            except Exception:
                pass
        self.sysproxy_value.configure(text=f"{label} {detail}".strip())
        self.sysproxy_btn.configure(text="关闭" if mode != "off" else "开启")

    def _on_proxy_state(self, running, port):
        # 延后一帧刷新，等 service 写完注册表
        self.after(200, self.refresh_sysproxy_status)

    def _toggle_sysproxy(self):
        mode = systemproxy.get_proxy_mode()
        enable = mode == "off"
        self.service.set_system_proxy_enabled(enable)
        self.refresh_sysproxy_status()

    def _save(self):
        sel = self.interval_combo.current()
        hours = self.INTERVAL_CHOICES[sel][1] if 0 <= sel < len(self.INTERVAL_CHOICES) else 0
        modes = ["pac", "global", "off"]
        self.cfg.update({
            "minimize_to_tray": self.mintray_var.get(),
            "auto_start_refresh": self.autorefresh_var.get(),
            "proxy_port": int(self.port_var.get()),
            "proxy_mode": modes[self.mode_combo.current()] if 0 <= self.mode_combo.current() < 3 else "pac",
            "auto_update_hours": hours,
            "hosts_source": self.hosts_var.get().strip(),
        })
        messagebox.showinfo("已保存",
                            "设置已保存。\n若修改了代理模式或端口，请到「总览」停止再启动加速以生效。",
                            parent=self)

    def _open_path(self, path):
        path = str(path)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path) if os.path.isfile(path) else path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
