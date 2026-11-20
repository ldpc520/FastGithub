# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：FastGithubPy。

用法：
    pyinstaller FastGithubPy.spec --noconfirm
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules("aiohttp")
hiddenimports += collect_submodules("PyQt6")
hiddenimports += ["pyqtgraph", "numpy"]

datas = []
datas += collect_data_files("aiohttp")
datas += [("resources/app.ico", "resources")]  # 软件图标
datas += [("resources/qtbase_zh_CN.qm", "resources")]  # Qt 控件中文翻译（右键菜单等）

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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
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
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FastGithubPy",
)
