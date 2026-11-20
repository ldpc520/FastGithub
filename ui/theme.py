"""暗色主题 QSS：参考 PyInstaller GUI 等工具的深紫黑风格，紫蓝强调色。"""

DARK_QSS = r"""
* {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QWidget#root {
    background: #1e1b2e;
}
QFrame#sidebar {
    background: #211e33;
    border: none;
    border-right: 1px solid #322d4a;
}
QFrame#content {
    background: #1e1b2e;
}
QLabel {
    color: #d5d3e8;
}
QLabel#appTitle {
    font-size: 18px;
    font-weight: bold;
    color: #b8a5ff;
    padding: 8px 12px 2px 12px;
}
QLabel#appSub {
    font-size: 11px;
    color: #8b86a8;
    padding: 0px 12px 8px 12px;
}
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: bold;
    color: #e8e4f8;
}
QLabel#h1 {
    font-size: 23px;
    font-weight: bold;
    color: #c9baff;
}
QLabel#h2 {
    font-size: 15px;
    font-weight: bold;
    color: #ded9f2;
}
QLabel#muted {
    color: #8b86a8;
    font-size: 12px;
}
QLabel#statusOn {
    color: #5ed7a8;
    font-weight: bold;
}
QLabel#statusOff {
    color: #ff7d95;
    font-weight: bold;
}
/* 顶部标题栏 */
QFrame#header {
    background: #262239;
    border: 1px solid #383153;
    border-radius: 10px;
}
/* 黄色提示条 */
QFrame#notice {
    background: #37311f;
    border: 1px solid #b8912f;
    border-radius: 8px;
}
QLabel#noticeText {
    color: #e8d08a;
    font-size: 12px;
}
QPushButton {
    background: #312d4a;
    color: #d5d3e8;
    border: 1px solid #443d63;
    border-radius: 6px;
    padding: 7px 14px;
}
QPushButton:hover {
    background: #3c3759;
    border-color: #5b5182;
}
QPushButton:pressed {
    background: #282440;
}
QPushButton#primary {
    background: #7c5cff;
    color: #ffffff;
    border: 1px solid #957cff;
    font-weight: bold;
}
QPushButton#primary:hover {
    background: #8d70ff;
}
QPushButton#danger {
    background: #4a2838;
    color: #ff8fa5;
    border: 1px solid #6e344b;
}
QPushButton#danger:hover {
    background: #5a3043;
}
QPushButton#nav {
    background: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 11px 16px;
    color: #9d98ba;
    font-size: 14px;
}
QPushButton#nav:hover {
    background: #2b2742;
    color: #ddd8f2;
}
QPushButton#nav:checked {
    background: #332d52;
    color: #bca9ff;
    border-left: 3px solid #8b6bff;
}
QFrame#card {
    background: #262239;
    border: 1px solid #383153;
    border-radius: 10px;
}
QFrame#divider {
    background: #383153;
    max-height: 1px;
}
QGroupBox {
    color: #c9baff;
    font-weight: bold;
    border: 1px solid #383153;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QTableWidget, QTreeWidget {
    background: #211e33;
    color: #d0cce4;
    border: 1px solid #383153;
    border-radius: 8px;
    gridline-color: #2e2947;
    selection-background-color: #4a3d7a;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #2d2843;
    color: #a49dbe;
    border: none;
    border-bottom: 1px solid #443d63;
    padding: 8px 6px;
    font-weight: bold;
}
QTableWidget::item {
    padding: 5px 6px;
}
QTreeWidget::item {
    padding: 7px 6px;
}
QTreeWidget::item:alternate, QTableWidget::item:alternate {
    background: #262240;
}
QLineEdit {
    background: #1b182b;
    color: #e0dcf2;
    border: 1px solid #443d63;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #4a3d7a;
}
QLineEdit:focus {
    border-color: #8b6bff;
}
QPlainTextEdit, QTextEdit {
    background: #171428;
    color: #a9a4c4;
    border: 1px solid #383153;
    border-radius: 8px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}
QCheckBox {
    color: #d0cce4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid #554b78;
    background: #1b182b;
}
QCheckBox::indicator:checked {
    background: #7c5cff;
    border-color: #957cff;
}
QComboBox {
    background: #1b182b;
    color: #e0dcf2;
    border: 1px solid #443d63;
    border-radius: 6px;
    padding: 7px 10px;
}
QComboBox QAbstractItemView {
    background: #262239;
    color: #e0dcf2;
    selection-background-color: #4a3d7a;
    border: 1px solid #443d63;
}
QSpinBox {
    background: #1b182b;
    color: #e0dcf2;
    border: 1px solid #443d63;
    border-radius: 6px;
    padding: 7px 8px;
}
QProgressBar {
    background: #1b182b;
    border: 1px solid #443d63;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: #7c5cff;
    border-radius: 6px;
}
QScrollArea {
    background: #1e1b2e;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: #1e1b2e;
}
QScrollBar:vertical {
    background: transparent; width: 10px;
}QScrollBar::handle:vertical {
    background: #443d63; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #5b5182;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QMenu {
    background: #262239;
    color: #d5d3e8;
    border: 1px solid #554b78;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 7px 22px; border-radius: 4px; }
QMenu::item:selected { background: #4a3d7a; }
QStatusBar {
    background: #211e33;
    color: #8b86a8;
    border-top: 1px solid #322d4a;
}
QToolTip {
    background: #322d4a;
    color: #e0dcf2;
    border: 1px solid #554b78;
}
"""


def apply_theme(app):
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
