"""节点测速页：github.akams.cn 节点聚合，测速排序，加速链接生成。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.nodes import NodeManager
from ui.widgets import card


class NodesPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._sort_col = 2
        self._build_ui()
        self._connect()
        self.load_nodes()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("GitHub 加速节点")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示
        head.addWidget(title)
        head.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(180)
        self.progress.setVisible(False)
        head.addWidget(self.progress)
        self.test_btn = QPushButton("⟳ 批量测速")
        self.test_btn.setObjectName("primary")
        head.addWidget(self.test_btn)
        root.addLayout(head)

        # 链接生成区
        gen_card, gen_layout = card("加速链接生成")
        row1 = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴 GitHub 链接，如 https://github.com/owner/repo/releases/download/v1.0/app.exe")
        self.node_combo = QComboBox()
        self.node_combo.setMinimumWidth(220)
        self.gen_btn = QPushButton("生成")
        self.copy_btn = QPushButton("复制结果")
        row1.addWidget(self.url_input, 1)
        row1.addWidget(self.node_combo)
        row1.addWidget(self.gen_btn)
        row1.addWidget(self.copy_btn)
        gen_layout.addLayout(row1)
        self.result_label = QLabel("生成的加速链接会显示在这里")
        self.result_label.setObjectName("muted")
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gen_layout.addWidget(self.result_label)
        root.addWidget(gen_card)

        # 节点表
        table_card, table_layout = card("公开节点列表（来自 github.akams.cn）")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["节点", "状态", "延迟(ms)", "地址"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        pal = self.table.palette()
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c2030"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#151822"))
        self.table.setPalette(pal)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().sectionClicked.connect(self._sort_by_col)
        table_layout.addWidget(self.table)
        root.addWidget(table_card, 1)

    def _connect(self):
        self.test_btn.clicked.connect(self._test)
        self.gen_btn.clicked.connect(self._generate)
        self.copy_btn.clicked.connect(self._copy)
        self.service.node_progress_signal.connect(self._on_progress)
        self.service.nodes_done_signal.connect(self._on_done)

    def _test(self):
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测速中…")
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.service.test_nodes()

    def _on_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _on_done(self, results):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("⟳ 批量测速")
        self.progress.setVisible(False)
        self.load_nodes(results)

    def load_nodes(self, results=None):
        results = results or self.service.nodemgr.results
        # 未测速时按原顺序，测速后按延迟
        self.table.setRowCount(len(results))
        for r, node in enumerate(results):
            self.table.setItem(r, 0, QTableWidgetItem(node.name))
            status = QTableWidgetItem("✓ 可用" if node.ok else "✗ 不可用")
            status.setForeground(QColor("#4ec9a0") if node.ok else QColor("#e06c75"))
            self.table.setItem(r, 1, status)
            lat = QTableWidgetItem(str(node.latency_ms) if node.ok else "-")
            self.table.setItem(r, 2, lat)
            self.table.setItem(r, 3, QTableWidgetItem(node.url))
        # 更新下拉框
        current = self.node_combo.currentData()
        self.node_combo.clear()
        ok_nodes = [n for n in results if n.ok]
        display = ok_nodes or results
        for n in display:
            self.node_combo.addItem(f"{n.name} ({n.latency_ms}ms)" if n.ok else n.name, n.url)
        if current:
            idx = self.node_combo.findData(current)
            if idx >= 0:
                self.node_combo.setCurrentIndex(idx)

    def _sort_by_col(self, col):
        self.table.sortItems(col, Qt.SortOrder.AscendingOrder)

    def _generate(self):
        url = self.url_input.text().strip()
        node_url = self.node_combo.currentData()
        if not url or not node_url:
            self.result_label.setText("请先输入 GitHub 链接并选择节点")
            return
        result = NodeManager.build_url(node_url, url)
        self.result_label.setText(result)
        self.result_label.setStyleSheet("color: #7f9dff;")

    def _copy(self):
        text = self.result_label.text()
        if not text or "显示在这里" in text or "请先" in text:
            QMessageBox.information(self, "提示", "还没有生成加速链接")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "已复制", "加速链接已复制到剪贴板")
