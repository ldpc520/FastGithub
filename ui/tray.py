"""系统托盘（pystray）：显示主界面 / 启停加速 / 更新 IP / 退出。

pystray 的 run() 会阻塞，因此放在独立守护线程；所有对 tkinter 主线程的
操作都通过 window.root.after(...) 派发，避免跨线程操作控件。
"""
from __future__ import annotations

import os
import sys
import threading

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from core.loghub import log


def _make_image() -> Image.Image:
    """优先用 app.ico，失败则用代码绘制紫色圆形闪电。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico = os.path.join(base, "resources", "app.ico")
    if os.path.exists(ico):
        try:
            return Image.open(ico).convert("RGBA")
        except Exception:
            pass
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill="#7c5cff")
    d.polygon([(36, 12), (20, 36), (31, 36), (27, 53), (45, 28), (34, 28)], fill="white")
    return img


class TrayController:
    def __init__(self, window):
        self.window = window
        self.root = window.root
        self.icon = None
        self._thread = None
        self._running = False
        self._toggle_item = None

    def start(self):
        self._toggle_item = MenuItem("启动加速", self._on_toggle, default=True)
        menu = Menu(
            MenuItem("显示主界面", self._on_show, default=True),
            self._toggle_item,
            MenuItem("更新 IP", self._on_refresh),
            Menu.SEPARATOR,
            MenuItem("退出", self._on_quit),
        )
        self.icon = Icon("FastGithubPy", _make_image(), "FastGithubPy", menu=menu)
        self._thread = threading.Thread(target=self._run, daemon=True, name="FastGithubPy-tray")
        self._thread.start()

    def _run(self):
        try:
            self.icon.run()
        except Exception as exc:
            log.warn(f"托盘线程退出：{exc}")

    def update_state(self, running, port):
        try:
            self._toggle_item.text = "停止加速" if running else "启动加速"
            self.icon.title = f"FastGithubPy - {'运行中' if running else '已停止'}"
        except Exception:
            pass

    def notify(self, title, message):
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def stop(self):
        """停止托盘并等待线程退出，确保系统托盘图标被移除（避免残留）。"""
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass
        # 等待托盘线程从 run() 返回，让图标完成从系统托盘的注销
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass

    # ---- 菜单回调（托盘线程）→ 派发到 UI 主线程 ----
    def _on_show(self, icon=None, item=None):
        self.root.after(0, self.window.show_window)

    def _on_toggle(self, icon=None, item=None):
        self.root.after(0, self.window.toggle_proxy)

    def _on_refresh(self, icon=None, item=None):
        self.root.after(0, self.service_refresh)

    def service_refresh(self):
        self.window.service.refresh_ips()

    def _on_quit(self, icon=None, item=None):
        self.root.after(0, self.window.quit_app)
