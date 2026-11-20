"""设置页：加速配置、开机自启、托盘、自动刷新、目录入口。"""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core import systemproxy
from core.config import CONFIG_DIR, IP_CACHE_FILE, LOG_DIR, LOG_FILE
from ui.widgets import ToggleRow, card, divider


class SettingsPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.cfg = service.cfg
        self._build_ui()
        self._connect()
        self._load()

    def _build_ui(self):
        # 用滚动区域承载内容，避免窗口高度不足时卡片被压缩重叠
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        root = QVBoxLayout(inner)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("设置")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示
        head.addWidget(title)
        head.addStretch(1)
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setObjectName("primary")
        head.addWidget(self.save_btn)
        root.addLayout(head)

        # 启动与运行
        run_card, run_layout = card("启动与运行")
        self.autostart = ToggleRow("开机自启", "登录 Windows 后自动启动并加速")
        self.mintray = ToggleRow("启动后最小化到托盘", "只在托盘显示图标，点击托盘恢复窗口")
        self.autorefresh = ToggleRow("启动后自动刷新 IP", "启动约 15 秒后自动测速一次")
        run_layout.addWidget(self.autostart)
        run_layout.addWidget(divider())
        run_layout.addWidget(self.mintray)
        run_layout.addWidget(divider())
        run_layout.addWidget(self.autorefresh)
        root.addWidget(run_card)

        # 代理设置
        proxy_card, proxy_layout = card("代理设置")
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("代理模式："))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("PAC 自动代理（仅 GitHub 走代理，推荐）", "pac")
        self.mode_combo.addItem("全局代理（所有网站走代理）", "global")
        self.mode_combo.addItem("不修改系统设置（手动配置）", "off")
        mode_row.addWidget(self.mode_combo, 1)
        proxy_layout.addLayout(mode_row)
        mode_hint = QLabel("PAC 模式只加速 GitHub，其它网站不受影响，程序未运行时也不会断网")
        mode_hint.setObjectName("muted")
        mode_hint.setWordWrap(True)
        proxy_layout.addWidget(mode_hint)
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("本地代理端口："))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setFixedWidth(100)
        port_row.addWidget(self.port_spin)
        port_row.addWidget(QLabel("（修改后需重启加速生效）"))
        port_row.addStretch(1)
        proxy_layout.addLayout(port_row)
        self.sysproxy_row = QHBoxLayout()
        self.sysproxy_label = QLabel("系统代理状态：")
        self.sysproxy_value = QLabel("-")
        self.sysproxy_btn = QPushButton("开启")
        self.sysproxy_btn.setFixedWidth(80)
        self.sysproxy_row.addWidget(self.sysproxy_label)
        self.sysproxy_row.addWidget(self.sysproxy_value)
        self.sysproxy_row.addStretch(1)
        self.sysproxy_row.addWidget(self.sysproxy_btn)
        proxy_layout.addLayout(self.sysproxy_row)
        self.sysproxy_btn.clicked.connect(self._toggle_sysproxy)
        root.addWidget(proxy_card)

        # IP 更新
        ip_card, ip_layout = card("IP 更新")
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("自动更新间隔："))
        self.interval_combo = QComboBox()
        self.interval_combo.addItem("不自动更新", 0)
        self.interval_combo.addItem("6 小时", 6)
        self.interval_combo.addItem("12 小时", 12)
        self.interval_combo.addItem("24 小时", 24)
        self.interval_combo.addItem("3 天", 72)
        interval_row.addWidget(self.interval_combo)
        interval_row.addStretch(1)
        ip_layout.addLayout(interval_row)
        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("hosts 源："))
        self.hosts_input = QLineEdit()
        self.hosts_input.setPlaceholderText("https://raw.hellogithub.com/hosts.json")
        host_row.addWidget(self.hosts_input, 1)
        ip_layout.addLayout(host_row)
        root.addWidget(ip_card)

        # 目录
        dir_card, dir_layout = card("目录与诊断")
        btn_row = QHBoxLayout()
        for name, path in [("配置目录", CONFIG_DIR), ("日志目录", LOG_DIR), ("IP 缓存", IP_CACHE_FILE)]:
            b = QPushButton(f"打开{name}")
            # clicked 会携带 checked(bool) 参数，显式接住再忽略，避免覆盖 path
            b.clicked.connect(lambda checked=False, p=path: self._open_path(p))
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        dir_layout.addLayout(btn_row)
        root.addWidget(dir_card)
        root.addStretch(1)

    def _connect(self):
        self.save_btn.clicked.connect(self._save)
        self.autostart.check.stateChanged.connect(self._on_autostart)

    def _load(self):
        self.autostart.setChecked(bool(self.cfg.get("auto_start", False)))
        self.mintray.setChecked(bool(self.cfg.get("minimize_to_tray", True)))
        self.autorefresh.setChecked(bool(self.cfg.get("auto_start_refresh", True)))
        self.port_spin.setValue(int(self.cfg.get("proxy_port", 38457)))
        self.hosts_input.setText(self.cfg.get("hosts_source", ""))
        mode = self.cfg.get("proxy_mode", "pac")
        idx = self.mode_combo.findData(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        hours = int(self.cfg.get("auto_update_hours", 0))
        idx = self.interval_combo.findData(hours)
        if idx >= 0:
            self.interval_combo.setCurrentIndex(idx)
        self._refresh_sysproxy_status()

    def _refresh_sysproxy_status(self):
        mode = systemproxy.get_proxy_mode()
        label = {"pac": "PAC 自动代理", "global": "全局代理", "off": "未启用"}.get(mode, "未知")
        detail = ""
        if mode == "global":
            detail = systemproxy.get_system_proxy().get("server", "")
        self.sysproxy_value.setText(f"{label} {detail}".strip())
        self.sysproxy_btn.setText("关闭" if mode != "off" else "开启")

    def _toggle_sysproxy(self):
        mode = systemproxy.get_proxy_mode()
        enable = mode == "off"
        self.service.set_system_proxy_enabled(enable)
        self._refresh_sysproxy_status()

    def _on_autostart(self, state):
        enable = state == Qt.CheckState.Checked.value
        self.service.set_auto_start(enable)

    def _save(self):
        self.cfg.update({
            "minimize_to_tray": self.mintray.isChecked(),
            "auto_start_refresh": self.autorefresh.isChecked(),
            "proxy_port": self.port_spin.value(),
            "proxy_mode": self.mode_combo.currentData(),
            "auto_update_hours": self.interval_combo.currentData(),
            "hosts_source": self.hosts_input.text().strip(),
        })
        QMessageBox.information(
            self, "已保存",
            "设置已保存。\n若修改了代理模式或端口，请到「总览」停止再启动加速以生效。",
        )

    def _open_path(self, path):
        path = str(path)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path) if os.path.isfile(path) else path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
