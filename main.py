"""FastGithubPy 入口：tkinter + tkwebui 界面 + github.akams.cn 节点功能。"""
from __future__ import annotations

import os
import sys
import socket
import tkinter as tk

# 允许以脚本方式直接运行（core / ui 包在项目根目录）
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0] if "\\" in __file__ else ".")

from core.loghub import log
from core.service import AppService
from ui.theme import apply_dark_theme
from ui.main_window import MainWindow

# 单实例锁：绑定本机固定端口，重复启动会绑定失败，从而避免多个托盘图标
_LOCK_SOCKET = None
_LOCK_PORT = 38459


def _acquire_single_instance() -> bool:
    global _LOCK_SOCKET
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _LOCK_SOCKET = s  # 持有引用，进程存活期间端口一直被占用
        return True
    except OSError:
        return False


def main():
    if not _acquire_single_instance():
        # 已有一个实例在运行，静默退出即可，不再创建第二个托盘图标
        return
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
