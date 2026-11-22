"""轻量信号总线：替代 PyQt 的 pyqtSignal，无任何 GUI 框架依赖。

后台线程（asyncio worker）里 emit() 只把参数线程安全地放入队列；
UI 主线程定时调用 pump_all() 把回调派发到主线程执行（tkinter 要求
所有控件操作都在主线程），从而完全解耦 core 与界面框架。
"""
from __future__ import annotations

import queue
import threading
from typing import Callable


class Signal:
    """一个可连接多个回调的信号，emit 线程安全、回调在主线程 pump 时执行。"""

    def __init__(self) -> None:
        self._callbacks: list[Callable] = []
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()

    def connect(self, cb: Callable) -> None:
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def disconnect(self, cb: Callable) -> None:
        with self._lock:
            if cb in self._callbacks:
                self._callbacks.remove(cb)

    def emit(self, *args) -> None:
        """任意线程调用：仅入队，不直接执行回调。"""
        self._queue.put(args)

    def emit_now(self, *args) -> None:
        """立即在当前线程同步派发（用于无需切线程的场景）。"""
        self._dispatch(args)

    def _dispatch(self, args: tuple) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(*args)
            except Exception as exc:  # 单个回调异常不影响其它回调与 UI 循环
                import traceback

                traceback.print_exc()

    def pump(self, limit: int = 200) -> int:
        """主线程调用：派发至多 limit 条待处理事件，返回处理条数。"""
        n = 0
        while n < limit:
            try:
                args = self._queue.get_nowait()
            except queue.Empty:
                break
            self._dispatch(args)
            n += 1
        return n

    def pending(self) -> int:
        return self._queue.qsize()


class SignalBus:
    """管理一组 Signal，提供统一 pump。"""

    def __init__(self, *names: str) -> None:
        self._signals: dict[str, Signal] = {}
        for name in names:
            self._signals[name] = Signal()
            setattr(self, name, self._signals[name])

    def pump_all(self, limit: int = 200) -> int:
        total = 0
        for sig in self._signals.values():
            total += sig.pump(limit)
        return total
