"""全局配置管理：JSON 持久化，默认项与运行时热更新。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "FastGithubPy"

# 程序根目录（exe 打包后兼容 sys._MEIPASS）
def app_root() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


ROOT = app_root()
CONFIG_DIR = ROOT / "config"
LOG_DIR = ROOT / "logs"
CONFIG_FILE = CONFIG_DIR / "settings.json"
IP_CACHE_FILE = CONFIG_DIR / "ipaddresses.json"
LOG_FILE = LOG_DIR / "fastgithubpy.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "proxy_port": 38457,
    "proxy_mode": "pac",  # pac=仅GitHub走代理(推荐) / global=全局代理 / off=不改系统设置
    "auto_start": False,
    "minimize_to_tray": True,
    "auto_update_hours": 0,
    "auto_start_refresh": True,
    "tray_notify": True,
    "dns_servers": [
        "223.5.5.5:53",
        "119.29.29.29:53",
        "180.76.76.76:53",
        "8.8.8.8:53",
    ],
    "hosts_source": "https://raw.hellogithub.com/hosts.json",
    "meta_api": "https://api.github.com/meta",
    "use_meta_api": True,
    "meta_expand_limit": 3,   # 每个 CIDR 段最多展开的候选 IP 数
    "meta_max_candidates": 24,  # 单域名 meta 候选总量上限
    "probe_timeout": 4.0,
    "failure_blacklist_sec": 90,
    "connect_timeout": 4.0,
    "accelerate_domains": [
        "github.com",
        "api.github.com",
        "gist.github.com",
        "codeload.github.com",
        "raw.githubusercontent.com",
        "assets-cdn.github.com",
        "githubusercontent.com",
        "github.io",
        "objects.githubusercontent.com",
    ],
    "selected_nodes": [],
    "theme": "dark",
    "last_refresh": "",
}


class Config:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    user = json.load(f)
                if isinstance(user, dict):
                    self._data.update(user)
            except Exception:
                pass

    def save(self) -> None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any], save: bool = True) -> None:
        self._data.update(values)
        if save:
            self.save()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)


# 内置 GitHub 核心域名候选 IP 池（官方入口，仅作兜底，仍要过探测）
BUILTIN_IPS: dict[str, list[str]] = {
    "github.com": [
        "140.82.114.4",
        "140.82.116.4",
        "140.82.113.4",
        "140.82.112.3",
        "20.205.243.166",
        "20.27.177.113",
    ],
    "api.github.com": [
        "140.82.114.6",
        "140.82.116.6",
        "140.82.113.6",
        "20.205.243.166",
    ],
    "gist.github.com": [
        "140.82.114.9",
        "140.82.116.9",
        "140.82.113.9",
    ],
    "codeload.github.com": [
        "140.82.114.10",
        "140.82.116.10",
        "140.82.113.10",
        "20.205.243.166",
    ],
    "raw.githubusercontent.com": [
        "185.199.108.133",
        "185.199.109.133",
        "185.199.110.133",
        "185.199.111.133",
    ],
    "githubusercontent.com": [
        "185.199.108.133",
        "185.199.109.133",
    ],
    "github.io": [
        "185.199.108.153",
        "185.199.109.153",
        "185.199.110.153",
        "185.199.111.153",
    ],
    "objects.githubusercontent.com": [
        "185.199.108.133",
        "185.199.111.133",
    ],
}
