"""仪表盘页：加速开关、实时指标、流量图、IP 候选列表。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import pyqtgraph as pg

from core.loghub import log
from ui.widgets import card, divider, metric_card


class DashboardPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._last_up = 0
        self._last_down = 0
        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # 标题行
        head = QHBoxLayout()
        title = QLabel("加速总览")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示，避免重复
        self.status_label = QLabel("● 已停止")
        self.status_label.setObjectName("statusOff")
        head.addWidget(title)
        head.addWidget(self.status_label)
        head.addStretch(1)
        self.toggle_btn = QPushButton("▶ 启动加速")
        self.toggle_btn.setObjectName("primary")
        self.toggle_btn.setFixedWidth(130)
        self.refresh_btn = QPushButton("⟳ 更新 IP")
        self.refresh_btn.setFixedWidth(110)
        head.addWidget(self.refresh_btn)
        head.addWidget(self.toggle_btn)
        root.addLayout(head)

        # 指标卡
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.card_status, self.v_status = metric_card("服务状态", "已停止", "#e06c75")
        self.card_port, self.v_port = metric_card("代理端口", "-", "#4f6bff")
        self.card_up, self.v_up = metric_card("上传流量", "0 B", "#7f9dff")
        self.card_down, self.v_down = metric_card("下载流量", "0 B", "#4ec9a0")
        for c in (self.card_status, self.card_port, self.card_up, self.card_down):
            metrics.addWidget(c)
        root.addLayout(metrics)

        # 流量图
        chart_card, chart_layout = card("实时流量（每秒采样）")
        chart_layout.setContentsMargins(8, 8, 8, 8)
        self.plot = pg.PlotWidget(background="#0d1016")
        self.plot.setMinimumHeight(160)
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.getAxis("left").setPen(pg.mkPen("#7c8398"))
        self.plot.getAxis("bottom").setPen(pg.mkPen("#7c8398"))
        self.plot.getAxis("left").setTextPen(pg.mkPen("#7c8398"))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen("#7c8398"))
        self.plot.addLegend(offset=(10, 6), labelTextColor="#9aa2b7")
        self.curve_up = self.plot.plot(pen=pg.mkPen("#7f9dff", width=2), name="上传")
        self.curve_down = self.plot.plot(pen=pg.mkPen("#4ec9a0", width=2), name="下载")
        chart_layout.addWidget(self.plot)
        root.addWidget(chart_card)

        # IP 表
        ip_card, ip_layout = card("域名 IP 候选（按延迟排序）")
        self.ip_table = QTableWidget(0, 4)
        self.ip_table.setHorizontalHeaderLabels(["域名", "最快 IP", "可用数", "延迟(ms)"])
        self.ip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            self.ip_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.ip_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ip_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ip_table.setAlternatingRowColors(True)
        pal = self.ip_table.palette()
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c2030"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#151822"))
        self.ip_table.setPalette(pal)
        self.ip_table.verticalHeader().setVisible(False)
        ip_layout.addWidget(self.ip_table)
        root.addWidget(ip_card, 1)

    def _connect(self):
        self.toggle_btn.clicked.connect(self._toggle)
        self.refresh_btn.clicked.connect(self._refresh)
        self.service.proxy_state_signal.connect(self.on_proxy_state)
        self.service.stats_signal.connect(self.on_stats)
        self.service.refresh_done_signal.connect(self.on_refresh_done)

    def _toggle(self):
        if self.service.proxy.running:
            self.service.stop_proxy()
            self.toggle_btn.setText("▶ 启动加速")
        else:
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setText("启动中…")
            self.service.start_proxy()

    def _refresh(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("测速中…")
        self.service.refresh_ips()

    def on_proxy_state(self, running: bool, port: int):
        self.toggle_btn.setEnabled(True)
        if running:
            self.status_label.setText("● 运行中")
            self.status_label.setObjectName("statusOn")
            self.v_status.setText("运行中")
            self.v_status.setStyleSheet("color: #4ec9a0;")
            self.v_port.setText(str(port))
            self.toggle_btn.setText("■ 停止加速")
        else:
            self.status_label.setText("● 已停止")
            self.status_label.setObjectName("statusOff")
            self.v_status.setText("已停止")
            self.v_status.setStyleSheet("color: #e06c75;")
            self.v_port.setText("-")
            self.toggle_btn.setText("▶ 启动加速")
        self.status_label.style().polish(self.status_label)

    def on_stats(self, stats):
        self.v_up.setText(self._fmt(stats.upload))
        self.v_down.setText(self._fmt(stats.download))
        # 流量图显示每秒增量
        history = stats.history
        ups = []
        downs = []
        for i, (u, d) in enumerate(history):
            pu = history[i - 1][0] if i > 0 else 0
            pd = history[i - 1][1] if i > 0 else 0
            ups.append(max(0, u - pu) / 1024)
            downs.append(max(0, d - pd) / 1024)
        self.curve_up.setData(ups)
        self.curve_down.setData(downs)

    @staticmethod
    def _fmt(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024
        return f"{n:.1f} TB"

    def on_refresh_done(self, result):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("⟳ 更新 IP")
        self.load_ips()

    def load_ips(self):
        rows = self.service.ipmgr.status_rows()
        self.ip_table.setRowCount(len(rows))
        for r, data in enumerate(rows):
            self.ip_table.setItem(r, 0, QTableWidgetItem(data["domain"]))
            self.ip_table.setItem(r, 1, QTableWidgetItem(data["best"]))
            self.ip_table.setItem(r, 2, QTableWidgetItem(str(data["count"])))
            self.ip_table.setItem(r, 3, QTableWidgetItem(str(data["latency"])))
            if data["latency"] and data["latency"] < 300:
                self.ip_table.item(r, 3).setForeground(pg.mkQColor("#4ec9a0"))
