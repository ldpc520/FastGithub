"""GitHub 链接转直链：把仓库文件页链接转成可直接访问/下载的 raw 直链，可选加速代理前缀。

参考 nav.sdyun.eu.org/tools/github-direct-link.html 的功能，用 Python 实现，便于在桌面软件中复用与测试。
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

# 可选的加速代理节点（值拼在直链前面，空串表示不使用）
PROXY_NODES: list[tuple[str, str]] = [
    ("不使用", ""),
    ("github.sdjy.eu.org", "https://github.sdjy.eu.org"),
    ("gh-proxy.org", "https://gh-proxy.org"),
    ("hk.gh-proxy.org", "https://hk.gh-proxy.org"),
    ("cdn.gh-proxy.org", "https://cdn.gh-proxy.org"),
    ("edgeone.gh-proxy.org", "https://edgeone.gh-proxy.org"),
]

_GH_HOSTS = {"github.com", "www.github.com"}

# github.com/owner/repo/<kind>/<ref...>/<path...>
_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/"
    r"(?P<kind>blob|raw|tree)/(?P<rest>.+)$",
    re.IGNORECASE,
)


def convert_one(link: str, proxy: str = "") -> str:
    """把单条 GitHub 链接转成直链。

    - blob / raw 文件页 → https://raw.githubusercontent.com/owner/repo/<ref>/<path>
    - tree 目录页       → https://codeload.github.com/owner/repo/zip/<ref>（下载整个分支）
    - 已是直链的保持原样
    - 非 GitHub 链接原样返回
    """
    raw = link.strip()
    if not raw:
        return ""
    # 去掉末尾 / 与查询串、锚点（raw 直链不需要）
    clean = raw.split("#", 1)[0].split("?", 1)[0].rstrip("/")

    parsed = urlparse(clean)
    host = (parsed.hostname or "").lower()

    # 已经是 raw / codeload 直链：保持原样
    if host in {"raw.githubusercontent.com", "codeload.github.com"}:
        return _with_proxy(clean, proxy)

    if host not in _GH_HOSTS:
        # 其它链接原样返回（不套代理，避免误伤）
        return raw

    m = _PATTERN.match(clean)
    if not m:
        return raw

    owner, repo, kind, rest = m.group("owner"), m.group("repo"), m.group("kind").lower(), m.group("rest")
    rest = unquote(rest).strip("/")

    if kind in ("blob", "raw"):
        direct = f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"
    else:  # tree → 打包下载
        # rest 形如 main/path/to/dir，zip 下载只需要 ref（第一段），路径忽略
        ref = rest.split("/", 1)[0]
        direct = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{ref}"

    return _with_proxy(direct, proxy)


def _with_proxy(direct: str, proxy: str) -> str:
    """给直链加代理前缀。ghproxy 通用格式：{proxy}/{原始直链}。"""
    p = (proxy or "").strip().rstrip("/")
    return f"{p}/{direct}" if p else direct


def convert_batch(text: str, proxy: str = "") -> str:
    """批量转换：每行一个链接，保留非空行的顺序。"""
    lines = [convert_one(line, proxy) for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
