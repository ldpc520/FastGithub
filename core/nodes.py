"""ghproxy 节点聚合（来自 github.akams.cn）：节点测速与加速链接生成。"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import aiohttp

from .loghub import log

# 始终置顶的自定义节点名称（测速排序后仍排最前）
PINNED_NAMES = {"风语轮迹"}

# 自定义置顶节点 + github.akams.cn 上的公开加速节点
NODES: list[tuple[str, str]] = [
    ("风语轮迹", "https://gh.sdjy.eu.org"),  # 用户自定义，置顶
    ("[贡献]gh.dpik.top", "https://gh.dpik.top"),
    ("[贡献]github.tbap.top", "https://github.tbap.top"),
    ("[贡献]ghfile.geekertao.top", "https://ghfile.geekertao.top"),
    ("[贡献]ghproxy.net", "https://ghproxy.net"),
    ("[贡献]gh-proxy.com", "https://gh-proxy.com"),
    ("[贡献]cdn.gh-proxy.com", "https://cdn.gh-proxy.com"),
    ("[贡献]github.dpik.top", "https://github.dpik.top"),
    ("[贡献]j.1lin.dpdns.org", "https://j.1lin.dpdns.org"),
    ("[贡献]github.starrlzy.cn", "https://github.starrlzy.cn"),
    ("[贡献]github-proxy.memory-echoes.cn", "https://github-proxy.memory-echoes.cn"),
    ("[贡献]git.yylx.win", "https://git.yylx.win"),
    ("[贡献]gh.927223.xyz", "https://gh.927223.xyz"),
    ("[贡献]gh.felicity.ac.cn", "https://gh.felicity.ac.cn"),
    ("[贡献]cdn.akaere.online", "https://cdn.akaere.online"),
    ("[贡献]github.mxw.qzz.io", "https://github.mxw.qzz.io"),
    ("[贡献]gh.acmsz.top", "https://gh.acmsz.top"),
    ("[测绘]slink.ltd", "https://slink.ltd"),
    ("[测绘]github.tmby.shop", "https://github.tmby.shop"),
    ("[测绘]ghpr.cc", "https://ghpr.cc"),
    ("[测绘]gh.tryxd.cn", "https://gh.tryxd.cn"),
    ("[测绘]gitproxy.click", "https://gitproxy.click"),
    ("[测绘]github.chenc.dev", "https://github.chenc.dev"),
    ("[测绘]gh.ddlc.top", "https://gh.ddlc.top"),
    ("[测绘]gitproxy.mrhjx.cn", "https://gitproxy.mrhjx.cn"),
    ("[测绘]gh.sixyin.com", "https://gh.sixyin.com"),
    ("[测绘]gh.monlor.com", "https://gh.monlor.com"),
    ("[测绘]ghpxy.hwinzniej.top", "https://ghpxy.hwinzniej.top"),
    ("[测绘]fastgit.cc", "https://fastgit.cc"),
    ("[测绘]ghproxy.1888866.xyz", "https://ghproxy.1888866.xyz"),
    ("[测绘]gh.idayer.com", "https://gh.idayer.com"),
    ("[测绘]github.ednovas.xyz", "https://github.ednovas.xyz"),
    ("[测绘]github.xxlab.tech", "https://github.xxlab.tech"),
    ("[测绘]ghproxy.icu", "https://ghproxy.icu"),
    ("[测绘]gh.beimengvv.xyz", "https://gh.beimengvv.xyz"),
    ("[贡献]githubdog.com", "https://githubdog.com"),
    ("[贡献]gh.meali.top", "https://gh.meali.top"),
    ("[贡献]gh.my-website.ccwu.cc", "https://gh.my-website.ccwu.cc"),
    ("[贡献]github.ikgy.top", "https://github.ikgy.top"),
    ("[贡献]cfgh.ikgy.top", "https://cfgh.ikgy.top"),
    ("[贡献]gh.ruan.dpdns.org", "https://gh.ruan.dpdns.org"),
    ("[贡献]ghproxy.felicity.land", "https://ghproxy.felicity.land"),
    ("[贡献]github.gohj99.site", "https://github.gohj99.site"),
]

# 测速用的小文件（GitHub raw 1 字节级请求）
PROBE_URL = "https://raw.githubusercontent.com/yuan71058/FastGithub/master/README.md"


@dataclass
class NodeResult:
    name: str
    url: str
    latency_ms: float = -1.0
    ok: bool = False
    note: str = ""


class NodeManager:
    def __init__(self) -> None:
        self.results: list[NodeResult] = [NodeResult(name, url) for name, url in NODES]

    async def test_all(self, progress_cb=None, concurrency: int = 10) -> list[NodeResult]:
        # 单个共享 session：若每个节点各建 session 却共用 connector，
        # 第一个 session 退出时会关闭 connector，导致其余节点全部 "Connector is closed"
        sem = asyncio.Semaphore(concurrency)
        timeout = aiohttp.ClientTimeout(total=12, connect=6)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FastGithubPy/1.0"}
        connector = aiohttp.TCPConnector(ssl=False, limit=concurrency)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
            async def test(node: NodeResult) -> NodeResult:
                async with sem:
                    target = f"{node.url.rstrip('/')}/{PROBE_URL}"
                    start = time.perf_counter()
                    try:
                        async with session.get(target) as resp:
                            # 只读前 4KB 判断是否可用；read() 不接受参数，必须用 content.read(n)
                            data = await resp.content.read(4096)
                            node.latency_ms = round((time.perf_counter() - start) * 1000, 1)
                            if resp.status in (200, 206) and len(data) > 0:
                                node.ok = True
                                node.note = f"HTTP {resp.status}"
                            else:
                                node.ok = False
                                node.note = f"HTTP {resp.status}"
                    except asyncio.TimeoutError:
                        node.ok = False
                        node.note = "Timeout"
                    except Exception as exc:
                        node.ok = False
                        node.note = type(exc).__name__
                    if progress_cb:
                        try:
                            progress_cb()
                        except Exception:
                            pass
                return node

            tasks = [asyncio.create_task(test(n)) for n in self.results]
            await asyncio.gather(*tasks, return_exceptions=True)
        ok = [n for n in self.results if n.ok]
        log.info(f"节点测速完成：{len(ok)}/{len(self.results)} 可用")
        # 置顶节点始终排最前，其余按可用性 + 延迟
        return sorted(
            self.results,
            key=lambda n: (n.name not in PINNED_NAMES, not n.ok, n.latency_ms if n.ok else 99999),
        )

    @staticmethod
    def build_url(node_url: str, github_url: str) -> str:
        """生成加速链接。"""
        github_url = github_url.strip()
        if not github_url:
            return ""
        if not github_url.startswith("http"):
            github_url = "https://" + github_url
        return f"{node_url.rstrip('/')}/{github_url}"

    @staticmethod
    def build_release_url(node_url: str, owner: str, repo: str, tag: str, filename: str) -> str:
        raw = f"https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"
        return NodeManager.build_url(node_url, raw)
