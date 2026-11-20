"""GitHub 直链转换页：blob 文件页链接 → raw 直链，支持批量、加速代理、实时转换。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.directlink import convert_batch
from ui.widgets import card


class DirectLinkPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("GitHub 直链转换")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示
        head.addWidget(title)
        head.addStretch(1)
        root.addLayout(head)

        # 输入卡片
        in_card, in_layout = card("粘贴 GitHub 链接（支持多行批量，每行一个）")
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "https://github.com/owner/repo/blob/main/path/to/file.txt\n"
            "https://github.com/owner/repo/tree/main/src"
        )
        self.input.setMinimumHeight(150)
        in_layout.addWidget(self.input)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("加速代理："))
        self.proxy_combo = QComboBox()
        self.proxy_combo.setMinimumWidth(260)
        # 数据源与「加速节点」页共享同一份 NodeManager，测速排序后这里同步反映
        self._fill_proxy_combo()
        opt_row.addWidget(self.proxy_combo)
        opt_row.addStretch(1)
        self.convert_btn = QPushButton("转换")
        self.convert_btn.setObjectName("primary")
        self.clear_btn = QPushButton("清空")
        self.copy_btn = QPushButton("复制全部")
        opt_row.addWidget(self.convert_btn)
        opt_row.addWidget(self.clear_btn)
        opt_row.addWidget(self.copy_btn)
        in_layout.addLayout(opt_row)
        root.addWidget(in_card)

        # 输出卡片
        out_card, out_layout = card("转换结果")
        hint = QLabel(
            "blob/raw 文件页 → raw 直链；tree 目录页 → zip 打包下载；每行一个，实时转换。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        out_layout.addWidget(hint)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(200)
        self.output.setPlaceholderText("转换结果会显示在这里")
        out_layout.addWidget(self.output, 1)
        root.addWidget(out_card)

    def _fill_proxy_combo(self):
        """用加速节点页同一份节点数据填充代理下拉（含「不使用」）。"""
        current_url = self.proxy_combo.currentData() if hasattr(self, "proxy_combo") else None
        self.proxy_combo.clear()
        self.proxy_combo.addItem("不使用（生成原始直链）", "")
        for node in self.service.nodemgr.results:
            label = node.name
            if node.ok and node.latency_ms >= 0:
                label += f"  ·  {node.latency_ms:.0f}ms"
            self.proxy_combo.addItem(label, node.url)
        # 尽量恢复之前选中的节点
        if current_url:
            idx = self.proxy_combo.findData(current_url)
            if idx >= 0:
                self.proxy_combo.setCurrentIndex(idx)

    def _connect(self):
        self.input.textChanged.connect(self._on_text_changed)
        self.proxy_combo.currentIndexChanged.connect(self._convert)
        self.convert_btn.clicked.connect(self._convert)
        self.clear_btn.clicked.connect(self._clear)
        self.copy_btn.clicked.connect(self._copy_all)
        # 加速节点页测速完成后，这里同步刷新节点列表与延迟
        self.service.nodes_done_signal.connect(self._on_nodes_done)

    def _on_nodes_done(self, _results):
        self._fill_proxy_combo()

    def _on_text_changed(self):
        self._convert()

    def _convert(self):
        proxy = self.proxy_combo.currentData() or ""
        result = convert_batch(self.input.toPlainText(), proxy)
        self.output.setPlainText(result)

    def _clear(self):
        self.input.clear()
        self.output.clear()

    def _copy_all(self):
        text = self.output.toPlainText().strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        self.copy_btn.setText("已复制 ✓")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("复制全部"))
