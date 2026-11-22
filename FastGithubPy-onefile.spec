# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 单文件打包配置：FastGithubPy。

单文件版：所有依赖打进一个 exe，双击即用，但启动比文件夹版慢几秒
（每次运行需解压到临时目录）。用法：
    pyinstaller FastGithubPy-onefile.spec --noconfirm
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules("aiohttp")
hiddenimports += collect_submodules("tkwebui")   # tkwebui 各组件按需动态导入
hiddenimports += collect_submodules("pystray")
hiddenimports += collect_submodules("PIL")
hiddenimports += ["tkinter"]

datas = []
datas += collect_data_files("aiohttp")
datas += [("resources/app.ico", "resources")]           # 软件图标

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# 单文件：把 binaries / datas 直接塞进 EXE，没有 COLLECT 步骤
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FastGithubPy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/app.ico",
)
