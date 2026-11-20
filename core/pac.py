"""PAC 自动代理：只为 GitHub 系域名走本地代理，其余网站直连。

PAC 文件持久化到配置目录，用 file:// URL 注册到 Windows 的 AutoConfigURL。
即使程序未运行、本地代理端口无人监听，也只有 GitHub 域名受影响，
其它网站在 PAC 规则里是 DIRECT，绝不会全网断网。
"""
from __future__ import annotations

import os
from pathlib import Path

from .config import CONFIG_DIR
from .loghub import log

PAC_FILE = CONFIG_DIR / "fastgithub.pac"

# 需要走代理的 GitHub 系域名（PAC 里做后缀匹配）
PROXY_DOMAINS = [
    "github.com",
    "githubusercontent.com",
    "github.io",
    "githubassets.com",
    "githubusercontent.com",
    "git.io",
    "gist.github.com",
]


def pac_url() -> str:
    """返回 PAC 文件的 file:// URL（Windows AutoConfigURL 用）。"""
    path = str(PAC_FILE.resolve()).replace("\\", "/")
    return "file:///" + path.lstrip("/")


def generate_pac(port: int) -> str:
    """生成 PAC 脚本内容。"""
    domains_js = ", ".join(f'"{d}"' for d in dict.fromkeys(PROXY_DOMAINS))
    return f"""// FastGithubPy 自动代理规则 - 仅 GitHub 系域名走代理
function FindProxyForURL(url, host) {{
    host = host.toLowerCase();
    var proxy = "PROXY 127.0.0.1:{port}";
    var direct = "DIRECT";

    // 本地地址一律直连
    if (isPlainHostName(host) || shExpMatch(host, "192.168.*") ||
        shExpMatch(host, "10.*") || shExpMatch(host, "127.*") ||
        host == "localhost") {{
        return direct;
    }}

    // GitHub 系域名（含子域）走本地代理
    var gh = [{domains_js}];
    for (var i = 0; i < gh.length; i++) {{
        if (host == gh[i] || dnsDomainIs(host, "." + gh[i])) {{
            return proxy;
        }}
    }}

    // 其它所有网站直连
    return direct;
}}
"""


def write_pac(port: int) -> str:
    """写入 PAC 文件，返回 file:// URL。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    content = generate_pac(port)
    PAC_FILE.write_text(content, encoding="utf-8")
    log.info(f"PAC 规则已生成：{PAC_FILE}（端口 {port}）")
    return pac_url()
