"""应用服务层：统一管理后端组件，给用户界面提供简洁的线程安全接口。

无 GUI 框架依赖：事件通过 core.signal.Signal 广播，UI 线程定时 pump。
"""
from __future__ import annotations

import asyncio
import sys
import threading
from typing import Callable

from .signal import Signal, SignalBus
from .config import Config
from .githubapi import GithubApi, Release
from .ipprobe import IpManager
from .loghub import log
from .nodes import NodeManager, NodeResult
from .proxy import LocalProxy
from . import systemproxy
from . import pac as pacmod


class AsyncWorker(threading.Thread):
    """承载独立 asyncio 事件循环的后台线程。"""

    def __init__(self, on_ready: Callable | None = None):
        super().__init__(daemon=True, name="FastGithubPy-async")
        self.loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._on_ready = on_ready

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        if self._on_ready:
            self._on_ready(self.loop)
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for t in pending:
            t.cancel()
        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._ready.wait(timeout)

    def submit(self, coro, callback: Callable | None = None):
        """从 UI 线程提交协程，完成后回调（回调在 worker 线程执行，emit 入队）。"""
        if not self.loop:
            self.wait_ready()
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
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


class AppService(SignalBus):
    """后端服务聚合，对外提供信号（由 UI pump）与操作方法。"""

    SIGNAL_NAMES = (
        "log_signal",           # (level, line)
        "stats_signal",         # (stats)
        "proxy_state_signal",   # (running, port)
        "refresh_done_signal",  # (result)
        "node_progress_signal", # (done, total)
        "nodes_done_signal",    # (results)
        "releases_done_signal", # (releases, owner, repo)
    )

    def __init__(self):
        super().__init__(*self.SIGNAL_NAMES)
        self.cfg = Config()
        self.ipmgr = IpManager(self.cfg)
        self.proxy = LocalProxy(self.cfg, self.ipmgr)
        self.nodemgr = NodeManager()
        self.github = GithubApi(self.cfg)
        self.worker = AsyncWorker(on_ready=self._on_loop_ready)
        self._proxy_backup: dict = {}
        self._actual_port = int(self.cfg.get("proxy_port", 38457))
        self._refreshing = False  # 防止启动检查与定时刷新重复发起测速

        log.set_callback(lambda level, line: self.log_signal.emit(level, line))
        self.proxy.set_stats_callback(lambda stats: self.stats_signal.emit(stats))

        # 启动自检：清除上次异常退出残留的系统代理（仅本程序残留）。
        if sys.platform == "win32":
            systemproxy.clear_stale_proxy(self._actual_port)

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
            if sys.platform == "win32":
                mode = self.cfg.get("proxy_mode", "pac")
                if mode == "pac":
                    url = pacmod.write_pac(port)
                    systemproxy.set_pac_proxy(True, url)
                elif mode == "global":
                    systemproxy.set_system_proxy(True, f"127.0.0.1:{port}", self._proxy_backup)
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
            log.info("加速服务已停止")

        self.worker.submit(task(), done)

    def refresh_ips(self, timeout_budget: float = 45.0):
        if self._refreshing:
            log.debug("已有 IP 测速在进行中，跳过重复刷新")
            return
        self._refreshing = True
        log.info("开始刷新 IP 测速…")

        def done(r):
            self._refreshing = False
            self.refresh_done_signal.emit(r)

        self.worker.submit(self.ipmgr.refresh_all(timeout_budget), done)

    def refresh_if_stale(self):
        """启动/定时检查：缓存有效则直接用缓存，仅缺失或过期时才测速。"""
        if not self.ipmgr.needs_refresh():
            log.info("IP 缓存有效，直接使用缓存（跳过本轮测速）")
            return
        self.refresh_ips()

    def start_auto_timer(self, root):
        """按 auto_update_hours 设置定时检查缓存新鲜度，0 表示不自动检查。"""
        hours = int(self.cfg.get("auto_update_hours", 0) or 0)
        if hours <= 0:
            return
        interval_ms = hours * 3600 * 1000
        root.after(interval_ms, self._auto_tick(root, interval_ms))

    def _auto_tick(self, root, interval_ms):
        def tick():
            self.refresh_if_stale()
            root.after(interval_ms, tick)
        return tick

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
