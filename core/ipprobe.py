"""IP 解析与优选：GitHub 官方 meta API + hosts 源 + 内置池 + DNS，TCP+TLS 双探测选最快 IP。"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from dataclasses import dataclass, field

import aiohttp

from .config import BUILTIN_IPS, IP_CACHE_FILE, Config
from .loghub import log


@dataclass
class Endpoint:
    ip: str
    latency_ms: float = 0.0
    ok: bool = False
    source: str = ""


@dataclass
class IpState:
    """单个域名的候选 IP 与运行时熔断状态。"""
    domain: str
    endpoints: list[Endpoint] = field(default_factory=list)
    best: str | None = None
    blacklist: dict[str, float] = field(default_factory=dict)
    last_refresh: float = 0.0


class IpManager:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.states: dict[str, IpState] = {}
        self._lock = asyncio.Lock()
        self._load_cache()

    # ---------------- 缓存 ----------------
    def _load_cache(self) -> None:
        if not IP_CACHE_FILE.exists():
            return
        try:
            with open(IP_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for domain, item in data.items():
                st = IpState(domain=domain)
                st.best = item.get("best")
                st.last_refresh = item.get("last_refresh", 0)
                for e in item.get("endpoints", []):
                    st.endpoints.append(
                        Endpoint(e["ip"], e.get("latency_ms", 0), e.get("ok", False), e.get("source", ""))
                    )
                self.states[domain] = st
        except Exception as exc:
            log.warn(f"读取 IP 缓存失败：{exc}")

    def _save_cache(self) -> None:
        try:
            data = {}
            for domain, st in self.states.items():
                data[domain] = {
                    "best": st.best,
                    "last_refresh": st.last_refresh,
                    "endpoints": [
                        {"ip": e.ip, "latency_ms": e.latency_ms, "ok": e.ok, "source": e.source}
                        for e in st.endpoints
                    ],
                }
            with open(IP_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            log.warn(f"保存 IP 缓存失败：{exc}")

    # ---------------- 候选来源 ----------------
    async def _fetch_hosts_source(self, session: aiohttp.ClientSession) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        url = self.cfg.get("hosts_source", "")
        if not url:
            return result
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                raw = await resp.text()
            items = json.loads(raw)
            for pair in items:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    ip, domain = str(pair[0]), str(pair[1]).lower().rstrip(".")
                    if ip and domain:
                        result.setdefault(domain, []).append(ip)
            log.info(f"hosts 源加载成功：{len(result)} 个域名")
        except Exception as exc:
            log.warn(f"hosts 源不可用：{exc}")
        return result

    # ---------------- GitHub 官方 meta API ----------------
    # 域名 → meta 分组映射（web/api/git 是 GitHub 主站核心分组）
    DOMAIN_META_GROUPS: dict[str, tuple[str, ...]] = {
        "github.com": ("web", "git"),
        "api.github.com": ("api",),
        "gist.github.com": ("web", "git"),
        "codeload.github.com": ("git", "web"),
        "raw.githubusercontent.com": ("web",),
        "githubusercontent.com": ("web",),
        "github.io": ("web", "pages"),
        "objects.githubusercontent.com": ("web",),
    }

    async def _fetch_meta(self, session: aiohttp.ClientSession) -> dict[str, list[str]]:
        """拉取 https://api.github.com/meta 的 CIDR 网段，按分组返回。"""
        result: dict[str, list[str]] = {}
        if not self.cfg.get("use_meta_api", True):
            return result
        url = self.cfg.get("meta_api", "https://api.github.com/meta")
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"Accept": "application/vnd.github+json"},
            ) as resp:
                if resp.status != 200:
                    log.warn(f"meta API 返回 HTTP {resp.status}")
                    return result
                data = await resp.json()
            for group, cidrs in data.items():
                if isinstance(cidrs, list):
                    result[group] = [str(c) for c in cidrs if isinstance(c, str)]
            log.info(
                f"GitHub meta 加载成功：web={len(result.get('web', []))} "
                f"api={len(result.get('api', []))} git={len(result.get('git', []))}"
            )
        except Exception as exc:
            log.warn(f"GitHub meta API 不可用：{exc}")
        return result

    @staticmethod
    def _expand_cidr(cidr: str, limit: int) -> list[str]:
        """把 CIDR 展开为可用单 IP：/32 直接用；大网段取前 limit 个（跳过网络/广播地址）。"""
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            if net.version != 4:
                return []
            if net.prefixlen == 32:
                return [str(net.network_address)]
            hosts = list(net.hosts())
            step = max(1, len(hosts) // limit)
            picked = [str(hosts[i]) for i in range(0, len(hosts), step)][:limit]
            return picked
        except Exception:
            return []

    def _collect_meta_ips(self, domain: str, meta: dict[str, list[str]]) -> list[str]:
        groups = self.DOMAIN_META_GROUPS.get(domain, ("web", "git"))
        limit = int(self.cfg.get("meta_expand_limit", 3))
        max_total = int(self.cfg.get("meta_max_candidates", 24))
        out: list[str] = []
        for group in groups:
            cidrs = meta.get(group, [])
            # /32 精确 IP 优先（更可能是真实入口）
            exact = [c for c in cidrs if c.endswith("/32")]
            broad = [c for c in cidrs if not c.endswith("/32")]
            for cidr in exact + broad:
                if len(out) >= max_total:
                    break
                for ip in self._expand_cidr(cidr, limit):
                    if ip not in out:
                        out.append(ip)
                    if len(out) >= max_total:
                        break
        return out

    @staticmethod
    def _ip_in_ranges(ip: str, cidrs: list[str]) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in ipaddress.ip_network(c, strict=False) for c in cidrs)
        except Exception:
            return False

    async def _dns_resolve(self, domain: str) -> list[str]:
        def resolve() -> list[str]:
            try:
                infos = socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
                return sorted({info[4][0] for info in infos})
            except Exception:
                return []

        return await asyncio.to_thread(resolve)

    def _collect_candidates(
        self, domain: str, hosts: dict[str, list[str]], meta: dict[str, list[str]] | None = None
    ) -> tuple[list[str], str]:
        out: list[str] = []
        source = ""
        # 1. GitHub 官方 meta API（权威来源，优先）
        meta_ips = self._collect_meta_ips(domain, meta or {})
        for ip in meta_ips:
            if ip not in out:
                out.append(ip)
        if meta_ips:
            source = "meta"
        # 2. hosts 源（含子域通配匹配），并用 meta 官方段做白名单校验
        official = meta.get("web", []) + meta.get("api", []) + meta.get("git", []) if meta else []
        for key, ips in hosts.items():
            if domain == key or (key.startswith("*.") and domain.endswith(key[1:])):
                for ip in ips:
                    # meta 可用时，过滤掉不在官方网段内的可疑 IP
                    if official and not self._ip_in_ranges(ip, official):
                        log.debug(f"过滤非官方 IP：{domain} -> {ip}")
                        continue
                    if ip not in out:
                        out.append(ip)
                        source = source or "hosts"
        # 3. 内置候选池兜底
        for ip in BUILTIN_IPS.get(domain, []):
            if ip not in out:
                out.append(ip)
                source = source or "builtin"
        return out, source

    # ---------------- 双探测 ----------------
    async def _probe_one(self, ip: str, domain: str, port: int = 443) -> Endpoint:
        """TCP 连接 + TLS 握手两段探测，都通过才算可用。"""
        ep = Endpoint(ip=ip)
        timeout = float(self.cfg.get("probe_timeout", 4.0))
        start = time.perf_counter()
        writer = None
        try:
            # TLS 握手：用域名做 SNI，不校验证书（中间路径可能改写）。
            # 必须把 ssl 上下文直接传给 open_connection——新版 Python（3.14+）
            # 下对 StreamReader 单独调用 ctx.wrap_socket() 会抛 AttributeError，
            # 导致所有探测被误判为失败。
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = asyncio.open_connection(ip, port, ssl=ctx, server_hostname=domain)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            ep.latency_ms = round((time.perf_counter() - start) * 1000, 1)
            ep.ok = True
        except Exception:
            ep.ok = False
        finally:
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
        return ep

    async def probe_domain(
        self, domain: str, hosts: dict[str, list[str]] | None = None, meta: dict[str, list[str]] | None = None
    ) -> IpState:
        async with self._lock:
            candidates, source = self._collect_candidates(domain, hosts or {}, meta)
            # DNS 回退：hosts/内置池没给够时补充
            if len(candidates) < 3:
                dns_ips = await self._dns_resolve(domain)
                for ip in dns_ips:
                    if ip not in candidates:
                        candidates.append(ip)
                        source = source or "dns"
            if not candidates:
                dns_ips = await self._dns_resolve(domain)
                candidates = dns_ips
                source = "dns"

            st = self.states.get(domain) or IpState(domain=domain)
            now = time.time()
            # 清理过期熔断
            black_sec = float(self.cfg.get("failure_blacklist_sec", 90))
            st.blacklist = {ip: t for ip, t in st.blacklist.items() if now - t < black_sec}
            usable = [ip for ip in candidates if ip not in st.blacklist]
            log.info(f"探测 {domain}：{len(usable)}/{len(candidates)} 个候选（来源 {source or 'none'}）")

            # 并发探测，限制并发度
            sem = asyncio.Semaphore(12)

            async def guarded(ip: str) -> Endpoint:
                async with sem:
                    return await self._probe_one(ip, domain)

            results = await asyncio.gather(*(guarded(ip) for ip in usable), return_exceptions=True)
            endpoints: list[Endpoint] = []
            for ip, res in zip(usable, results):
                if isinstance(res, Exception):
                    endpoints.append(Endpoint(ip=ip, ok=False))
                else:
                    res.source = source
                    endpoints.append(res)

            ok_list = sorted([e for e in endpoints if e.ok], key=lambda e: e.latency_ms)
            if not ok_list and st.endpoints:
                # 全部失败时保留旧 IP（交给实际请求验证），不把可用地址清空
                log.warn(f"{domain} 本轮无可用 IP，保留上次结果 {st.best}")
                st.last_refresh = now
                self.states[domain] = st
                return st

            st.endpoints = ok_list or endpoints
            st.best = ok_list[0].ip if ok_list else (st.best or (candidates[0] if candidates else None))
            st.last_refresh = now
            self.states[domain] = st
            self._save_cache()
            if ok_list:
                log.info(f"{domain} 最快 IP：{st.best} ({ok_list[0].latency_ms}ms)")
            return st

    async def refresh_all(self, timeout_budget: float = 45.0) -> dict[str, IpState]:
        """刷新全部加速域名，带软超时预算。"""
        domains = list(self.cfg.get("accelerate_domains", []))
        async with aiohttp.ClientSession() as session:
            hosts, meta = await asyncio.gather(
                self._fetch_hosts_source(session),
                self._fetch_meta(session),
            )

        async def one(domain: str) -> IpState:
            try:
                return await self.probe_domain(domain, hosts, meta)
            except Exception as exc:
                log.warn(f"探测 {domain} 异常：{exc}")
                return self.states.get(domain) or IpState(domain=domain)

        tasks = [asyncio.create_task(one(d)) for d in domains]
        done, pending = await asyncio.wait(tasks, timeout=timeout_budget)
        for t in pending:
            t.cancel()
        if pending:
            log.warn(f"刷新超时，{len(pending)} 个域名后台未完成（已完成的 IP 立即生效）")
        return {d: self.states[d] for d in domains if d in self.states}

    def get_best(self, domain: str) -> str | None:
        domain = domain.lower().rstrip(".")
        st = self.states.get(domain)
        if st and st.best:
            return st.best
        # 精确未命中时尝试通配
        for key, s in self.states.items():
            if key.startswith("*.") and domain.endswith(key[1:]) and s.best:
                return s.best
        return None

    def report_failure(self, domain: str, ip: str) -> None:
        """请求阶段失败：拉黑该 IP 90 秒。"""
        st = self.states.get(domain)
        if not st:
            return
        st.blacklist[ip] = time.time()
        alive = [e for e in st.endpoints if e.ip != ip and e.ok]
        alive.sort(key=lambda e: e.latency_ms)
        st.endpoints = alive
        st.best = alive[0].ip if alive else None
        log.warn(f"{domain} 上游 {ip} 失败，已拉黑 90 秒，切换至 {st.best or '无'}")

    def status_rows(self) -> list[dict]:
        rows = []
        for domain, st in self.states.items():
            rows.append(
                {
                    "domain": domain,
                    "best": st.best or "-",
                    "count": len([e for e in st.endpoints if e.ok]),
                    "latency": st.endpoints[0].latency_ms if st.endpoints and st.endpoints[0].ok else 0,
                    "last_refresh": st.last_refresh,
                }
            )
        return sorted(rows, key=lambda r: r["domain"])
