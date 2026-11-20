"""日志中心：写入文件并广播给 UI（通过 callback）。"""
from __future__ import annotations

import datetime as dt
import threading
from collections import deque
from typing import Callable

from .config import LOG_FILE


class LogHub:
    def __init__(self, max_lines: int = 3000) -> None:
        self._lock = threading.Lock()
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._callback: Callable[[str, str], None] | None = None
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def set_callback(self, cb: Callable[[str, str], None] | None) -> None:
        self._callback = cb

    def log(self, level: str, message: str) -> None:
        ts = dt.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        with self._lock:
            self._lines.append(line)
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {message}\n")
            except Exception:
                pass
            cb = self._callback
        if cb:
            try:
                cb(level, line)
            except Exception:
                pass

    def info(self, msg: str) -> None:
        self.log("INFO", msg)

    def warn(self, msg: str) -> None:
        self.log("WARN", msg)

    def error(self, msg: str) -> None:
        self.log("ERROR", msg)

    def debug(self, msg: str) -> None:
        self.log("DEBUG", msg)

    def history(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()


log = LogHub()
