"""日志页：实时日志流、级别过滤、清空。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.loghub import log
from ui.widgets import card


class LogsPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._build_ui()
        self.service.log_signal.connect(self.on_log)
        for line in log.history():
            self._append(line)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        head = QHBoxLayout()
        title = QLabel("运行日志")
        title.setObjectName("h1")
        title.setVisible(False)  # 顶部标题栏已显示
        head.addWidget(title)
        head.addStretch(1)
        self.autoscroll = QCheckBox("自动滚动")
        self.autoscroll.setChecked(True)
        head.addWidget(self.autoscroll)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear)
        head.addWidget(clear_btn)
        root.addLayout(head)

        log_card, log_layout = card()
        self.edit = QPlainTextEdit()
        self.edit.setReadOnly(True)
        self.edit.setMaximumBlockCount(3000)
        log_layout.addWidget(self.edit)
        root.addWidget(log_card, 1)

    def on_log(self, level: str, line: str):
        self._append(line)

    def _append(self, line: str):
        self.edit.appendPlainText(line)
        if self.autoscroll.isChecked():
            self.edit.verticalScrollBar().setValue(self.edit.verticalScrollBar().maximum())

    def _clear(self):
        self.edit.clear()
        log.clear()
