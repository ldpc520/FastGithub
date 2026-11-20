"""本地 HTTP 正向代理：支持 CONNECT 隧道，按域名选最快 IP 转发，统计流量。"""
from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass, field

from .config import Config
from .ipprobe import IpManager
from .loghub import log


@dataclass
class TrafficStats:
    upload: int = 0
    download: int = 0
    requests: int = 0
    active: int = 0
    failures: int = 0
    history: list[tuple[int, int]] = field(default_factory=list)  # (up, down) 每秒采样


class LocalProxy:
    def __init__(self, cfg: Config, ipmgr: IpManager) -> None:
        self.cfg = cfg
        self.ipmgr = ipmgr
        self.stats = TrafficStats()
        self.server: asyncio.AbstractServer | None = None
        self._running = False
        self._on_stats = None

    def set_stats_callback(self, cb) -> None:
        self._on_stats = cb

    async def start(self, port: int | None = None) -> int:
        if self._running:
            return port or self.cfg.get("proxy_port", 38457)
        port = port or int(self.cfg.get("proxy_port", 38457))
        # 端口占用时向上顺延
        for attempt in range(20):
            try:
                self.server = await asyncio.start_server(self._handle, "127.0.0.1", port)
                self._running = True
                asyncio.create_task(self._sampler())
                log.info(f"本地代理已启动：http://127.0.0.1:{port}")
                return port
            except OSError:
                port += 1
        raise RuntimeError("无法找到可用代理端口")

    async def stop(self) -> None:
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        log.info("本地代理已停止")

    @property
    def running(self) -> bool:
        return self._running

    async def _sampler(self) -> None:
        while self._running:
            await asyncio.sleep(1)
            self.stats.history.append((self.stats.upload, self.stats.download))
            if len(self.stats.history) > 120:
                self.stats.history.pop(0)
            if self._on_stats:
                try:
                    self._on_stats(self.stats)
                except Exception:
                    pass

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.stats.active += 1
        self.stats.requests += 1
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=15)
            if not line:
                return
            parts = line.decode("iso-8859-1").strip().split()
            if len(parts) < 2:
                return
            method, target = parts[0].upper(), parts[1]
            # 读取请求头
            headers: dict[str, str] = {}
            while True:
                h = await asyncio.wait_for(reader.readline(), timeout=15)
                if h in (b"\r\n", b"\n", b""):
                    break
                k, _, v = h.decode("iso-8859-1").partition(":")
                headers[k.strip().lower()] = v.strip()

            if method == "CONNECT":
                await self._tunnel(target, reader, writer)
            else:
                await self._forward_http(method, target, headers, reader, writer)
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            log.debug(f"代理连接异常：{exc}")
        finally:
            self.stats.active -= 1
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _resolve_target(self, host: str, port: int) -> tuple[str, int]:
        """把域名换成测速得到的最快 IP，端口不变。"""
        best = self.ipmgr.get_best(host)
        if best:
            log.debug(f"{host}:{port} -> {best}:{port}")
            return best, port
        return host, port

    async def _tunnel(self, target: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        host, _, port_s = target.partition(":")
        port = int(port_s or 443)
        remote_host, remote_port = self._resolve_target(host, port)
        timeout = float(self.cfg.get("connect_timeout", 4.0))
        try:
            remote_r, remote_w = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port), timeout=timeout
            )
        except Exception as exc:
            self.stats.failures += 1
            self.ipmgr.report_failure(host, remote_host)
            log.warn(f"CONNECT {target} 连接失败：{exc}")
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
            return
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await self._pipe(reader, writer, remote_r, remote_w)

    async def _forward_http(
        self,
        method: str,
        target: str,
        headers: dict[str, str],
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(target)
        host = parsed.hostname or headers.get("host", "").split(":")[0]
        port = parsed.port or 80
        remote_host, remote_port = self._resolve_target(host, port)
        timeout = float(self.cfg.get("connect_timeout", 4.0))
        try:
            remote_r, remote_w = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port), timeout=timeout
            )
        except Exception as exc:
            self.stats.failures += 1
            log.warn(f"{target} 连接失败：{exc}")
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
            return

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        req = [f"{method} {path} HTTP/1.1", f"Host: {host}"]
        for k, v in headers.items():
            if k not in ("proxy-connection", "proxy-authorization", "host"):
                req.append(f"{k}: {v}")
        remote_w.write(("\r\n".join(req) + "\r\n\r\n").encode("iso-8859-1"))
        body = await reader.read()
        if body:
            remote_w.write(body)
        await remote_w.drain()
        await self._pipe(reader, writer, remote_r, remote_w)

    async def _pipe(
        self,
        client_r: asyncio.StreamReader,
        client_w: asyncio.StreamWriter,
        remote_r: asyncio.StreamReader,
        remote_w: asyncio.StreamWriter,
    ) -> None:
        async def c2r() -> None:
            try:
                while True:
                    data = await client_r.read(65536)
                    if not data:
                        break
                    self.stats.upload += len(data)
                    remote_w.write(data)
                    await remote_w.drain()
            except Exception:
                pass
            finally:
                try:
                    remote_w.close()
                except Exception:
                    pass

        async def r2c() -> None:
            try:
                while True:
                    data = await remote_r.read(65536)
                    if not data:
                        break
                    self.stats.download += len(data)
                    client_w.write(data)
                    await client_w.drain()
            except Exception:
                pass
            finally:
                try:
                    client_w.close()
                except Exception:
                    pass

        await asyncio.gather(c2r(), r2c(), return_exceptions=True)
