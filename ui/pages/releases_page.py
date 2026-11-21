"""Releases 页：查询仓库发布列表，一键生成各节点的加速下载链接。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QColor, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.githubapi import Release
from core.nodes import NodeManager
from ui.widgets import card


class ReleasesPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._releases: list[Release] = []
        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        head = QHBoxLayout()
        title = QLabel("Releases 加速下载")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示
        head.addWidget(title)
        head.addStretch(1)
        root.addLayout(head)

        search_card, search_layout = card("查询仓库")
        row = QHBoxLayout()
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("输入 owner/repo，如 tidain/YunX-Desktop")
        self.repo_input.setMinimumWidth(320)
        self.repo_input.returnPressed.connect(self._search)
        self.search_btn = QPushButton("查询 Releases")
        self.search_btn.setObjectName("primary")
        row.addWidget(self.repo_input, 1)
        row.addWidget(self.search_btn)
        row.addStretch(1)
        search_layout.addLayout(row)
        root.addWidget(search_card)

        tree_card, tree_layout = card("发布列表（右键资源直接用浏览器下载）")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["版本 / 资源", "大小", "下载次数"])
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setIndentation(20)  # 子节点缩进更明显
        self.tree.setRootIsDecorated(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree_layout.addWidget(self.tree)
        root.addWidget(tree_card, 1)

    def _connect(self):
        self.search_btn.clicked.connect(self._search)
        self.service.releases_done_signal.connect(self._on_releases)
        self.tree.customContextMenuRequested.connect(self._context_menu)

    def _search(self):
        text = self.repo_input.text().strip()
        # 兼容 owner/repo、完整 GitHub URL、git@ 地址
        text = text.strip().rstrip("/")
        if text.startswith("https://github.com/"):
            text = text[len("https://github.com/"):]
        elif text.startswith("http://github.com/"):
            text = text[len("http://github.com/"):]
        elif text.startswith("git@github.com:"):
            text = text[len("git@github.com:"):]
        parts = [p for p in text.split("/") if p]
        if len(parts) < 2:
            QMessageBox.information(self, "提示", "请按 owner/repo 格式输入，如 tidain/YunX-Desktop")
            return
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        self.search_btn.setEnabled(False)
        self.search_btn.setText("查询中…")
        self.service.fetch_releases(owner, repo)

    def _on_releases(self, releases, owner, repo):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("查询 Releases")
        self._releases = releases
        self.tree.clear()
        if not releases:
            QMessageBox.warning(self, "无结果", f"没有获取到 {owner}/{repo} 的 Releases，可能仓库不存在或网络受限")
            return
        for rel in releases:
            top = QTreeWidgetItem([f"{rel.tag}  {rel.name}", "", rel.published_at])
            top.setData(0, Qt.ItemDataRole.UserRole, ("release", rel))
            top.setForeground(0, QColor("#a792ff"))
            top_font = top.font(0)
            top_font.setBold(True)
            top_font.setPointSize(11)
            top.setFont(0, top_font)
            for col in range(3):
                top.setSizeHint(col, QSize(120, 34))  # 版本行更高
            for asset in rel.assets:
                child = QTreeWidgetItem([
                    asset.name,
                    f"{asset.size / 1048576:.1f} MB",
                    str(asset.downloads),
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, ("asset", asset))
                child.setData(3, Qt.ItemDataRole.UserRole, rel.tag)
                child.setForeground(0, QColor("#c9c6de"))
                for col in range(3):
                    child.setSizeHint(col, QSize(120, 30))  # 资源行 30px，不再挤成一团
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)

    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "asset":
            return
        asset = data[1]
        menu = QMenu(self)
        nodes = [n for n in self.service.nodemgr.results if n.ok][:8]
        if not nodes:
            nodes = self.service.nodemgr.results[:8]
        # 首选：直接用默认浏览器打开下载
        for node in nodes:
            menu.addAction(f"用 {node.name} 下载（浏览器）", lambda n=node: self._open_download(n, asset))
        # 备选：复制链接
        copy_menu = menu.addMenu("复制加速链接…")
        for node in nodes:
            copy_menu.addAction(node.name, lambda n=node: self._copy_link(n, asset))
        menu.addAction("复制原始 GitHub 直链", lambda: self._copy_raw(asset))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _open_download(self, node, asset):
        """用系统默认浏览器打开加速下载链接，直接触发浏览器下载。"""
        url = NodeManager.build_url(node.url, asset.browser_download_url)
        QDesktopServices.openUrl(QUrl(url))

    def _copy_link(self, node, asset):
        url = NodeManager.build_url(node.url, asset.browser_download_url)
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, "已复制", f"加速链接已复制：\n{url}")

    def _copy_raw(self, asset):
        QApplication.clipboard().setText(asset.browser_download_url)
        QMessageBox.information(self, "已复制", f"原始直链已复制：\n{asset.browser_download_url}")
