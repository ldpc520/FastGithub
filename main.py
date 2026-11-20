"""FastGithubPy 入口：用 PyQt6 复刻 FastGithub 界面 + github.akams.cn 节点功能。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTranslator, QLibraryInfo
from PyQt6.QtWidgets import QApplication

# 允许以脚本方式直接运行（core / ui 包在项目根目录）
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0] if "\\" in __file__ else ".")

from core.service import AppService
from ui.main_window import MainWindow
from ui.theme import apply_theme


def _install_chinese_translators(app: QApplication):
    """加载 Qt 中文翻译：让输入框右键菜单、对话框按钮等标准控件全变中文。

    兼容源码运行与 PyInstaller 打包（sys._MEIPASS）两种路径。
    """
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "resources"))
    candidates.append(str(Path(__file__).resolve().parent / "resources"))
    try:
        candidates.append(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    except Exception:
        pass

    loaded = []
    for qm in ("qtbase_zh_CN.qm", "qt_zh_CN.qm"):
        for d in candidates:
            p = os.path.join(d, qm)
            if not os.path.isfile(p):
                continue
            tr = QTranslator(app)
            if tr.load(p) and app.installTranslator(tr):
                loaded.append(tr)  # 保持引用，否则翻译会被 GC 回收失效
                break
    app._zh_translators = loaded


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    _install_chinese_translators(app)
    apply_theme(app)

    service = AppService()
    minimized = "--minimized" in sys.argv
    window = MainWindow(service, minimized=minimized)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
