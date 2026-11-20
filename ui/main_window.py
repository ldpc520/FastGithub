"""主窗口：左侧导航 + 页面栈 + 系统托盘。"""
from __future__ import annotations

import sys
import os

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.loghub import log
from ui.pages.dashboard import DashboardPage
from ui.pages.directlink_page import DirectLinkPage
from ui.pages.logs_page import LogsPage
from ui.pages.nodes_page import NodesPage
from ui.pages.releases_page import ReleasesPage
from ui.pages.settings_page import SettingsPage


def _icon_path() -> str:
    """兼容源码运行与 PyInstaller 打包后的资源路径。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "app.ico")


def make_icon() -> QIcon:
    """优先加载生成的 ico 图标，读取失败则回退到代码绘制。"""
    path = _icon_path()
    if os.path.exists(path):
        icon = QIcon(path)
        if not icon.isNull():
            return icon
    # 回退：代码绘制
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor("#4f6bff")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QBrush(QColor("#ffffff")))
    # 闪电
    pts = [
        QPointF(36, 12),
        QPointF(20, 36),
        QPointF(31, 36),
        QPointF(27, 53),
        QPointF(45, 28),
        QPointF(34, 28),
    ]
    p.drawPolygon(QPolygonF(pts))
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    PAGES = [
        ("总览", "📊", DashboardPage),
        ("加速节点", "🌐", NodesPage),
        ("Releases", "📦", ReleasesPage),
        ("直链转换", "🔗", DirectLinkPage),
        ("日志", "📝", LogsPage),
        ("设置", "⚙", SettingsPage),
    ]

    def __init__(self, service, minimized=False):
        super().__init__()
        self.service = service
        self.setWindowTitle("FastGithubPy - GitHub 加速工具箱")
        self.setWindowIcon(make_icon())
        self.resize(1060, 720)
        self.setMinimumSize(900, 620)
        self._drag_pos = None
        self._build_ui()
        self._build_tray()
        self._connect()
        if minimized or service.cfg.get("minimize_to_tray", True):
            QTimer.singleShot(100, self.hide)
        else:
            self.show()

        # 启动后自动刷新 IP
        if service.cfg.get("auto_start_refresh", True):
            QTimer.singleShot(15000, service.refresh_ips)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 16, 0, 12)
        sl.setSpacing(2)

        title = QLabel("FastGithubPy")
        title.setObjectName("appTitle")
        sub = QLabel("GitHub 加速工具箱")
        sub.setObjectName("appSub")
        sl.addWidget(title)
        sl.addWidget(sub)

        line = QFrame()
        line.setObjectName("divider")
        sl.addWidget(line)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.stack = QStackedWidget()
        for i, (name, emoji, cls) in enumerate(self.PAGES):
            btn = QPushButton(f" {emoji}   {name}")
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(btn, i)
            sl.addWidget(btn)
            page = cls(self.service)
            self.stack.addWidget(page)

        sl.addStretch(1)
        self.nav_group.buttonClicked.connect(self._on_nav)
        self.nav_group.button(0).setChecked(True)

        version = QLabel("v1.0")
        version.setObjectName("muted")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(version)

        layout.addWidget(sidebar)

        # 右侧：顶部标题栏 + 提示条 + 页面栈
        right = QFrame()
        right.setObjectName("content")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.setSpacing(12)

        header = QFrame()
        header.setObjectName("header")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.setSpacing(3)
        self.header_title = QLabel("GitHub 加速工具箱")
        self.header_title.setObjectName("h1")
        self.header_sub = QLabel("本地代理 + 官方 IP 优选 + ghproxy 节点聚合")
        self.header_sub.setObjectName("muted")
        hl.addWidget(self.header_title)
        hl.addWidget(self.header_sub)
        rl.addWidget(header)

        notice = QFrame()
        notice.setObjectName("notice")
        nl = QHBoxLayout(notice)
        nl.setContentsMargins(12, 8, 12, 8)
        warn = QLabel("⚠")
        warn.setStyleSheet("font-size: 16px; color: #e8c05a;")
        ntext = QLabel("首次使用请点「更新 IP」测速，再点「启动加速」；程序会自动设置/还原系统代理。")
        ntext.setObjectName("noticeText")
        ntext.setWordWrap(True)
        nl.addWidget(warn)
        nl.addWidget(ntext, 1)
        rl.addWidget(notice)

        rl.addWidget(self.stack, 1)
        layout.addWidget(right, 1)
        self.setStyleSheet(self.styleSheet())

    def _build_tray(self):
        icon = make_icon()
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("FastGithubPy")
        menu = QMenu()
        show_act = menu.addAction("显示主界面")
        show_act.triggered.connect(self._show_window)
        self.toggle_act = menu.addAction("启动加速")
        self.toggle_act.triggered.connect(self._toggle_proxy)
        refresh_act = menu.addAction("更新 IP")
        refresh_act.triggered.connect(self.service.refresh_ips)
        menu.addSeparator()
        quit_act = menu.addAction("退出")
        quit_act.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self.service.proxy_state_signal.connect(self._on_proxy_state)

    def _connect(self):
        pass

    HEADER_TEXT = {
        0: ("加速总览", "一键启停本地代理，查看实时流量与域名 IP 优选结果"),
        1: ("GitHub 加速节点", "github.akams.cn 公开节点测速，一键生成加速下载链接"),
        2: ("Releases 加速下载", "查询仓库发布列表，右键资源用节点生成加速链接"),
        3: ("GitHub 直链转换", "把文件页链接转成 raw 直链，支持批量与加速代理"),
        4: ("运行日志", "实时日志流，排障与状态追踪"),
        5: ("设置", "启动、代理、IP 更新与目录诊断"),
    }

    def _on_nav(self, btn):
        idx = self.nav_group.id(btn)
        self.stack.setCurrentIndex(idx)
        title, sub = self.HEADER_TEXT.get(idx, ("", ""))
        self.header_title.setText(title)
        self.header_sub.setText(sub)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _toggle_proxy(self):
        if self.service.proxy.running:
            self.service.stop_proxy()
        else:
            self.service.start_proxy()

    def _on_proxy_state(self, running, port):
        self.toggle_act.setText("停止加速" if running else "启动加速")
        if self.service.cfg.get("tray_notify", True):
            self.tray.showMessage(
                "FastGithubPy",
                f"加速服务已{'启动' if running else '停止'}" + (f"（端口 {port}）" if running else ""),
                make_icon(),
                2500,
            )

    def _quit(self):
        self.service.shutdown()
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        # 关闭按钮隐藏到托盘，不真正退出
        event.ignore()
        self.hide()
        if self.service.cfg.get("tray_notify", True):
            self.tray.showMessage("FastGithubPy", "已最小化到托盘", make_icon(), 2000)
