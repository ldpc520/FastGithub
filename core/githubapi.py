"""GitHub Releases 列表获取（经本地代理或直连）。"""
from __future__ import annotations

from dataclasses import dataclass, field

import aiohttp

from .config import Config
from .loghub import log


@dataclass
class ReleaseAsset:
    name: str
    size: int
    downloads: int
    browser_download_url: str


@dataclass
class Release:
    tag: str
    name: str
    published_at: str
    body: str
    assets: list[ReleaseAsset] = field(default_factory=list)


class GithubApi:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    async def fetch_releases(self, owner: str, repo: str, proxy: str | None = None) -> list[Release]:
        url = f"https://api.github.com/repos/{owner.strip()}/{repo.strip()}/releases?per_page=10"
        connector = None
        if proxy:
            connector = aiohttp.TCPConnector()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "FastGithubPy",
        }
        try:
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.get(url, proxy=proxy) as resp:
                    if resp.status != 200:
                        log.warn(f"获取 Releases 失败：HTTP {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as exc:
            log.error(f"获取 Releases 异常：{exc}")
            return []

        result = []
        for item in data:
            assets = [
                ReleaseAsset(
                    name=a.get("name", ""),
                    size=a.get("size", 0),
                    downloads=a.get("download_count", 0),
                    browser_download_url=a.get("browser_download_url", ""),
                )
                for a in item.get("assets", [])
            ]
            result.append(
                Release(
                    tag=item.get("tag_name", ""),
                    name=item.get("name", "") or item.get("tag_name", ""),
                    published_at=item.get("published_at", "")[:10],
                    body=(item.get("body") or "")[:500],
                    assets=assets,
                )
            )
        log.info(f"{owner}/{repo} 获取到 {len(result)} 个 Release")
        return result
