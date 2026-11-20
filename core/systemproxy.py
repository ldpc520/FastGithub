"""系统代理开关与开机自启（Windows 注册表，非管理员即可写 HKCU）。"""
from __future__ import annotations

import sys
from typing import Any

from .loghub import log

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FastGithubPy"


def _winreg():
    if sys.platform != "win32":
        return None
    import winreg

    return winreg


def get_system_proxy() -> dict[str, Any]:
    wr = _winreg()
    if not wr:
        return {"enabled": False, "server": ""}
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, REG_PATH, 0, wr.KEY_READ)
        try:
            try:
                enabled = bool(wr.QueryValueEx(key, "ProxyEnable")[0])
            except FileNotFoundError:
                enabled = False
            try:
                server = str(wr.QueryValueEx(key, "ProxyServer")[0])
            except FileNotFoundError:
                server = ""
            try:
                override = str(wr.QueryValueEx(key, "ProxyOverride")[0])
            except FileNotFoundError:
                override = ""
            return {"enabled": enabled, "server": server, "override": override}
        finally:
            wr.CloseKey(key)
    except Exception as exc:
        log.warn(f"读取系统代理失败：{exc}")
        return {"enabled": False, "server": ""}


def get_proxy_mode() -> str:
    """返回当前系统代理模式：pac / global / off。"""
    wr = _winreg()
    if not wr:
        return "off"
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, REG_PATH, 0, wr.KEY_READ)
        try:
            try:
                auto = str(wr.QueryValueEx(key, "AutoConfigURL")[0])
            except FileNotFoundError:
                auto = ""
            try:
                enabled = bool(wr.QueryValueEx(key, "ProxyEnable")[0])
            except FileNotFoundError:
                enabled = False
            if auto:
                return "pac"
            if enabled:
                return "global"
            return "off"
        finally:
            wr.CloseKey(key)
    except Exception:
        return "off"


def set_pac_proxy(enable: bool, pac_file_url: str = "") -> bool:
    """开启/关闭 PAC 自动代理模式，并互斥地关闭全局代理。

    enable=True 时必须传入 PAC 文件的 file:// URL。
    """
    wr = _winreg()
    if not wr:
        return False
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, REG_PATH, 0, wr.KEY_SET_VALUE | wr.KEY_READ)
        try:
            if enable:
                if not pac_file_url:
                    return False
                # 关闭全局代理，避免与 PAC 冲突
                wr.SetValueEx(key, "ProxyEnable", 0, wr.REG_DWORD, 0)
                wr.SetValueEx(key, "AutoConfigURL", 0, wr.REG_SZ, pac_file_url)
                log.info(f"已开启 PAC 自动代理：{pac_file_url}")
            else:
                # 清除 PAC，不动 ProxyServer（保留给用户手动设置的可能）
                try:
                    wr.DeleteValue(key, "AutoConfigURL")
                except FileNotFoundError:
                    pass
                log.info("已关闭 PAC 自动代理")
        finally:
            wr.CloseKey(key)
        try:
            import ctypes

            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        except Exception:
            pass
        return True
    except Exception as exc:
        log.error(f"设置 PAC 代理失败：{exc}")
        return False


def clear_stale_proxy(port: int = 38457, pac_marker: str = "fastgithub.pac") -> bool:
    """清除本程序残留的代理设置（软退出/系统重启导致未清理时）。

    仅清除指向本程序端口的全局代理，或本程序生成的 PAC（按文件名标记），
    绝不碰用户自己配置的其它代理。
    """
    wr = _winreg()
    if not wr:
        return False
    cleared = False
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, REG_PATH, 0, wr.KEY_SET_VALUE | wr.KEY_READ)
        try:
            # 1) 残留 PAC：按文件名标记识别
            try:
                auto = str(wr.QueryValueEx(key, "AutoConfigURL")[0])
            except FileNotFoundError:
                auto = ""
            if auto and pac_marker.lower() in auto.lower():
                try:
                    wr.DeleteValue(key, "AutoConfigURL")
                    cleared = True
                    log.info("已清除上次残留的 PAC 自动代理")
                except FileNotFoundError:
                    pass

            # 2) 残留全局代理：仅当指向本程序端口才清除
            try:
                enabled = bool(wr.QueryValueEx(key, "ProxyEnable")[0])
            except FileNotFoundError:
                enabled = False
            try:
                server = str(wr.QueryValueEx(key, "ProxyServer")[0])
            except FileNotFoundError:
                server = ""
            if enabled and str(port) in server:
                wr.SetValueEx(key, "ProxyEnable", 0, wr.REG_DWORD, 0)
                try:
                    wr.DeleteValue(key, "ProxyServer")
                except FileNotFoundError:
                    pass
                try:
                    wr.DeleteValue(key, "ProxyOverride")
                except FileNotFoundError:
                    pass
                cleared = True
                log.info(f"已清除上次残留的系统代理（端口 {port}）")
        finally:
            wr.CloseKey(key)
        return cleared
    except Exception as exc:
        log.warn(f"清除残留代理失败：{exc}")
        return False


def set_system_proxy(enable: bool, address: str = "127.0.0.1:38457", backup: dict | None = None) -> bool:
    wr = _winreg()
    if not wr:
        log.warn("非 Windows 平台，请手动设置系统代理")
        return False
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, REG_PATH, 0, wr.KEY_SET_VALUE | wr.KEY_READ)
        try:
            if enable:
                # 与 PAC 模式互斥：先清掉 AutoConfigURL
                try:
                    wr.DeleteValue(key, "AutoConfigURL")
                except FileNotFoundError:
                    pass
                # 首次开启时备份原设置
                if backup is not None and not backup.get("saved"):
                    backup["server"] = get_system_proxy().get("server", "")
                    backup["enabled"] = get_system_proxy().get("enabled", False)
                    backup["override"] = get_system_proxy().get("override", "")
                    backup["saved"] = True
                wr.SetValueEx(key, "ProxyEnable", 0, wr.REG_DWORD, 1)
                wr.SetValueEx(key, "ProxyServer", 0, wr.REG_SZ, address)
                # 本地地址绕过代理
                wr.SetValueEx(key, "ProxyOverride", 0, wr.REG_SZ, "localhost;127.0.0.1;<local>")
                log.info(f"已开启系统代理：{address}")
            else:
                wr.SetValueEx(key, "ProxyEnable", 0, wr.REG_DWORD, 0)
                if backup and backup.get("saved"):
                    wr.SetValueEx(key, "ProxyServer", 0, wr.REG_SZ, backup.get("server", ""))
                    wr.SetValueEx(key, "ProxyOverride", 0, wr.REG_SZ, backup.get("override", ""))
                log.info("已关闭系统代理")
        finally:
            wr.CloseKey(key)
        # 通知系统刷新代理设置
        try:
            import ctypes

            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        except Exception:
            pass
        return True
    except Exception as exc:
        log.error(f"设置系统代理失败：{exc}")
        return False


def set_auto_start(enable: bool, exe_path: str) -> bool:
    wr = _winreg()
    if not wr:
        return False
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, RUN_PATH, 0, wr.KEY_SET_VALUE | wr.KEY_READ)
        try:
            if enable:
                wr.SetValueEx(key, APP_NAME, 0, wr.REG_SZ, f'"{exe_path}" --minimized')
                log.info("已开启开机自启")
            else:
                try:
                    wr.DeleteValue(key, APP_NAME)
                    log.info("已关闭开机自启")
                except FileNotFoundError:
                    pass
        finally:
            wr.CloseKey(key)
        return True
    except Exception as exc:
        log.error(f"设置开机自启失败：{exc}")
        return False


def is_auto_start() -> bool:
    wr = _winreg()
    if not wr:
        return False
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, RUN_PATH, 0, wr.KEY_READ)
        try:
            wr.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            wr.CloseKey(key)
    except Exception:
        return False
