"""仪表盘页：加速开关、实时指标、IP 候选列表。"""
from __future__ import annotations

from tkinter import ttk

from core.loghub import log
from ui.widgets import card, make_table, metric_card
from ui.theme import COLORS


class DashboardPage(ttk.Frame):
    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self._build_ui()
        self.service.proxy_state_signal.connect(self.on_proxy_state)
        self.service.stats_signal.connect(self.on_stats)
        self.service.refresh_done_signal.connect(self.on_refresh_done)

    def _build_ui(self):
        # 顶部操作行
        head = ttk.Frame(self)
        head.pack(fill="x", pady=(0, 14))
        self.status_label = ttk.Label(head, text="● 已停止", style="StatusOff.TLabel")
        self.status_label.pack(side="left")
        ttk.Frame(head, width=20).pack(side="left")
        self.refresh_btn = ttk.Button(head, text="⟳ 更新 IP", width=12, command=self._refresh)
        self.refresh_btn.pack(side="right", padx=(0, 8))
        self.toggle_btn = ttk.Button(head, text="▶ 启动加速", width=14,
                                     style="Primary.TButton", command=self._toggle)
        self.toggle_btn.pack(side="right")

        # 指标卡
        metrics = ttk.Frame(self)
        metrics.pack(fill="x", pady=(0, 14))
        for i in range(4):
            metrics.columnconfigure(i, weight=1, uniform="metric")
        self.card_status, self.v_status = metric_card(metrics, "服务状态", "已停止", COLORS["red"])
        self.card_port, self.v_port = metric_card(metrics, "代理端口", "-", COLORS["blue"])
        self.card_up, self.v_up = metric_card(metrics, "上传流量", "0 B", COLORS["blue"])
        self.card_down, self.v_down = metric_card(metrics, "下载流量", "0 B", COLORS["green"])
        for i, c in enumerate((self.card_status, self.card_port, self.card_up, self.card_down)):
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))

        # IP 表
        ip_wrap, ip_body = card(self, "域名 IP 候选（按延迟排序）")
        ip_wrap.pack(fill="both", expand=True)
        self.ip_frame, self.ip_table = make_table(
            ip_body,
            [("domain", "域名", 240), ("best", "最快 IP", 150),
             ("count", "可用数", 80), ("latency", "延迟(ms)", 100)],
            height=8,
        )
        self.ip_frame.pack(fill="both", expand=True)
        self.load_ips()

    # ---------- 交互 ----------
    def _toggle(self):
        if self.service.proxy.running:
            self.service.stop_proxy()
        else:
            self.toggle_btn.configure(text="启动中…", state="disabled")
            self.service.start_proxy()

    def _refresh(self):
        self.refresh_btn.configure(text="测速中…", state="disabled")
        self.service.refresh_ips()

    # ---------- 信号回调（主线程） ----------
    def on_proxy_state(self, running: bool, port: int):
        self.toggle_btn.configure(state="normal")
        if running:
            self.status_label.configure(text="● 运行中", style="StatusOn.TLabel")
            self.v_status.configure(text="运行中", foreground=COLORS["green"])
            self.v_port.configure(text=str(port))
            self.toggle_btn.configure(text="■ 停止加速")
        else:
            self.status_label.configure(text="● 已停止", style="StatusOff.TLabel")
            self.v_status.configure(text="已停止", foreground=COLORS["red"])
            self.v_port.configure(text="-")
            self.toggle_btn.configure(text="▶ 启动加速")

    def on_stats(self, stats):
        self.v_up.configure(text=self._fmt(stats.upload))
        self.v_down.configure(text=self._fmt(stats.download))

    def on_refresh_done(self, result):
        self.refresh_btn.configure(text="⟳ 更新 IP", state="normal")
        self.load_ips()

    def load_ips(self):
        for row in self.ip_table.get_children():
            self.ip_table.delete(row)
        for idx, data in enumerate(self.service.ipmgr.status_rows()):
            tag = ("oddrow",) if idx % 2 else ()
            self.ip_table.insert("", "end", values=(
                data["domain"], data["best"], str(data["count"]), str(data["latency"])
            ), tags=tag)

    @staticmethod
    def _fmt(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024
        return f"{n:.1f} TB"
