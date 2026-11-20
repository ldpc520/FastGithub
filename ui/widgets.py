"""可复用 UI 控件：卡片、开关行、指标卡。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        lbl = QLabel(title)
        lbl.setObjectName("h2")
        layout.addWidget(lbl)
    return frame, layout


def metric_card(title: str, value: str = "-", accent: str = "#4f6bff") -> tuple[QFrame, QLabel]:
    frame = QFrame()
    frame.setObjectName("card")
    frame.setMinimumHeight(86)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("muted")
    v = QLabel(value)
    v.setObjectName("h1")
    v.setStyleSheet(f"color: {accent};")
    layout.addWidget(t)
    layout.addWidget(v)
    return frame, v


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFixedHeight(1)
    return line


class ToggleRow(QWidget):
    def __init__(self, title: str, description: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(10)
        # 标题与描述合并为一个富文本标签，避免嵌套布局高度计算异常
        text = f"<b>{title}</b>"
        if description:
            text += f'<br><span style="color:#8b86a8;font-size:11px;">{description}</span>'
        self.title = QLabel(text)
        self.title.setTextFormat(Qt.TextFormat.RichText)
        self.title.setWordWrap(True)
        self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.title, 1)
        self.check = QCheckBox()
        self.check.setChecked(checked)
        self.check.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.check)
        if description:
            self.setToolTip(description)

    def isChecked(self) -> bool:
        return self.check.isChecked()

    def setChecked(self, value: bool) -> None:
        self.check.setChecked(value)
