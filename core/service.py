"""应用服务层：统一管理后端组件，给用户界面提供简洁的线程安全接口。"""
from __future__ import annotations

import asyncio
import sys
from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .config import Config
from .githubapi import GithubApi, Release
from .ipprobe import IpManager
from .loghub import log
from .nodes import NodeManager, NodeResult
from .proxy import LocalProxy
from . import systemproxy
from . import pac as pacmod


class AsyncWorker(QThread):
    """承载独立 asyncio 事件循环的后台线程。"""
    loop_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stop = asyncio.Event() if False else None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop_ready.emit(self.loop)
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for t in pending:
            t.cancel()
        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def submit(self, coro, callback: Callable | None = None):
        """从 UI 线程提交协程，完成后回调（主线程）。"""
        if not self.loop:
            return
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        if callback:
            def done(f):
                try:
                    callback(f.result())
                except Exception as exc:
                    log.error(f"回调异常：{exc}")
            future.add_done_callback(done)

    def stop_loop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


class AppService(QObject):
    # 信号
    log_signal = pyqtSignal(str, str)
    stats_signal = pyqtSignal(object)
    proxy_state_signal = pyqtSignal(bool, int)
    refresh_done_signal = pyqtSignal(object)
    node_progress_signal = pyqtSignal(int, int)
    nodes_done_signal = pyqtSignal(object)
    releases_done_signal = pyqtSignal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = Config()
        self.ipmgr = IpManager(self.cfg)
        self.proxy = LocalProxy(self.cfg, self.ipmgr)
        self.nodemgr = NodeManager()
        self.github = GithubApi(self.cfg)
        self.worker = AsyncWorker(self)
        self._proxy_backup: dict = {}
        self._actual_port = int(self.cfg.get("proxy_port", 38457))

        log.set_callback(lambda level, line: self.log_signal.emit(level, line))
        self.proxy.set_stats_callback(lambda stats: self.stats_signal.emit(stats))

        # 启动自检：清除上次异常退出（如重启电脑）残留的系统代理，
        # 防止程序未运行时代理仍开着导致全网断网。不影响用户自己的代理。
        if sys.platform == "win32":
            systemproxy.clear_stale_proxy(self._actual_port)

        self.worker.loop_ready.connect(self._on_loop_ready)
        self.worker.start()

    def _on_loop_ready(self, loop):
        log.info("异步服务已就绪")

    # ---------- 代理控制 ----------
    def start_proxy(self):
        async def task():
            port = await self.proxy.start()
            self._actual_port = port
            return port

        def done(port):
            self.proxy_state_signal.emit(True, port)
            # 按配置应用系统代理模式（Windows）
            if sys.platform == "win32":
                mode = self.cfg.get("proxy_mode", "pac")
                if mode == "pac":
                    url = pacmod.write_pac(port)
                    systemproxy.set_pac_proxy(True, url)
                elif mode == "global":
                    systemproxy.set_system_proxy(True, f"127.0.0.1:{port}", self._proxy_backup)
                # off: 不改系统代理，用户自行配置
            log.info(f"加速服务运行中，代理端口 {port}，模式 {self.cfg.get('proxy_mode', 'pac')}")

        self.worker.submit(task(), done)

    def stop_proxy(self):
        async def task():
            await self.proxy.stop()

        def done(_):
            self.proxy_state_signal.emit(False, self._actual_port)
            if sys.platform == "win32":
                mode = self.cfg.get("proxy_mode", "pac")
                if mode == "pac":
                    systemproxy.set_pac_proxy(False)
                elif mode == "global":
                    systemproxy.set_system_proxy(False, backup=self._proxy_backup)
                    self._proxy_backup = {}
                # off: 未改过系统设置，无需清理
            log.info("加速服务已停止")

        self.worker.submit(task(), done)

    def refresh_ips(self, timeout_budget: float = 45.0):
        log.info("开始刷新 IP 测速…")
        self.worker.submit(self.ipmgr.refresh_all(timeout_budget), lambda r: self.refresh_done_signal.emit(r))

    # ---------- 节点测速 ----------
    def test_nodes(self):
        total = len(self.nodemgr.results)
        counter = {"n": 0}

        def progress():
            counter["n"] += 1
            self.node_progress_signal.emit(counter["n"], total)

        async def task():
            return await self.nodemgr.test_all(progress_cb=progress)

        self.worker.submit(task(), lambda r: self.nodes_done_signal.emit(r))

    # ---------- Releases ----------
    def fetch_releases(self, owner: str, repo: str):
        proxy = f"http://127.0.0.1:{self._actual_port}" if self.proxy.running else None

        def done(result):
            self.releases_done_signal.emit(result, owner, repo)

        self.worker.submit(self.github.fetch_releases(owner, repo, proxy), done)

    # ---------- 设置 ----------
    def set_system_proxy_enabled(self, enable: bool):
        if sys.platform != "win32":
            return
        mode = self.cfg.get("proxy_mode", "pac")
        if mode == "pac":
            if enable:
                url = pacmod.write_pac(self._actual_port)
                systemproxy.set_pac_proxy(True, url)
            else:
                systemproxy.set_pac_proxy(False)
        else:
            addr = f"127.0.0.1:{self._actual_port}"
            systemproxy.set_system_proxy(enable, addr, self._proxy_backup)

    def set_auto_start(self, enable: bool):
        import os
        exe = sys.executable
        if getattr(sys, "frozen", False):
            run_path = exe
        else:
            run_path = f'{exe} "{sys.argv[0]}"'
        if sys.platform == "win32":
            systemproxy.set_auto_start(enable, run_path)
        self.cfg.set("auto_start", enable)

    def shutdown(self):
        try:
            if self.proxy.running:
                if sys.platform == "win32":
                    mode = self.cfg.get("proxy_mode", "pac")
                    if mode == "pac":
                        systemproxy.set_pac_proxy(False)
                    elif mode == "global":
                        systemproxy.set_system_proxy(False, backup=self._proxy_backup)
            self.worker.stop_loop()
        except Exception:
            pass
