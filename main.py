"""FastGithubPy 入口：tkinter + tkwebui 界面 + github.akams.cn 节点功能。"""
from __future__ import annotations

import os
import sys
import tkinter as tk

# 允许以脚本方式直接运行（core / ui 包在项目根目录）
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0] if "\\" in __file__ else ".")

from core.loghub import log
from core.service import AppService
from ui.theme import apply_dark_theme
from ui.main_window import MainWindow


def main():
    from tkwebui import enable_dpi_awareness

    enable_dpi_awareness()
    root = tk.Tk()
    apply_dark_theme(root)

    service = AppService()
    window = MainWindow(root, service)

    # 启动后约 15 秒自动刷新 IP
    if service.cfg.get("auto_start_refresh", True):
        root.after(15000, service.refresh_ips)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            service.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
