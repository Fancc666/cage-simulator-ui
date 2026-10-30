# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 —— 文件夹版（onedir，方案 B）

用法::

    cd UI
    .venv/bin/pip install pyinstaller
    .venv/bin/pyinstaller CageSim.spec

产物在 ``dist/CageSim/``。

分发结构（把 ``CagePython/`` 整个拷到可执行文件旁边）::

    CageSim/
    ├─ CageSim.exe          ← Windows；macOS/Linux 下是 CageSim
    ├─ _internal/           ← PyInstaller 运行时（勿动）
    └─ CagePython/          ← 原始计算程序，用户可自行维护
         ├─ state.py
         ├─ read_input.py
         ├─ ...              （共 16 个 .py）
         ├─ WAMIT_5S.1
         ├─ WAMIT_5S.3
         ├─ WAMIT_5S.9
         ├─ WAMIT_5S.GDF
         ├─ WAMIT_5S1.hst
         └─ WAMIT_5S1.mmx

运行时由 ``app.paths.program_dir_default()`` 定位到「可执行文件同级」的
``CagePython/`` 目录。若用户在界面里手动指定了程序目录，则以界面设置为准
（保存在同级的 ``settings.json``）。

注意
----
``CagePython/`` **不打包进 exe**，这是刻意的：
  * 用户可替换 WAMIT 文件、修改原始计算代码，无需重新打包；
  * 16 个模块名过于通用（``state``/``rk44`` 等），打包进来容易与
    第三方包重名，运行时反而更难排查。
"""

import os

# --------------------------------------------------------------------------- #
#  基本配置
# --------------------------------------------------------------------------- #
APP_NAME = "CageSim"
ENTRY = "main.py"

# 图标（可选）：把 app.ico / app.icns 放进 assets/ 即自动启用
_ICON_CANDIDATES = ["assets/app.ico", "assets/app.icns", "assets/icon.ico"]
ICON = next((p for p in _ICON_CANDIDATES if os.path.exists(p)), None)

# --------------------------------------------------------------------------- #
#  原始计算程序的模块名（运行时从外部 CagePython/ 目录加载，不打包）
# --------------------------------------------------------------------------- #
PROGRAM_MODULES = [
    "state", "plot_style", "matlab_compat", "read_input",
    "rk44", "dfdt_eqmot", "xiboli", "xibo_dangenlan",
    "motion_simu_parameters", "fftfiltering_hz", "hit_spek3",
    "wavestatistic", "jonswap_h",
    "read_wamit1_file", "read_wamit234_file", "read_wamit9_file",
]

# --------------------------------------------------------------------------- #
#  只在本程序里用到的后端 / 可选依赖，显式排除以减小体积
# --------------------------------------------------------------------------- #
OTHER_BACKENDS = [
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_qt5",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_wxagg",
    "IPython", "jupyter", "notebook", "pytest",
    "tkinter.test", "test",
]


# --------------------------------------------------------------------------- #
#  打包
# --------------------------------------------------------------------------- #
a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=[],
    # matplotlib 的 Tk 内嵌画布需要显式声明（静态分析发现不了）
    hiddenimports=[
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends._backend_tk",
        "PIL._tkinter_finder",
        "scipy.io",
        "scipy.signal",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=PROGRAM_MODULES + OTHER_BACKENDS,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir：依赖放到 _internal/
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX 常被杀软误报，关掉
    console=False,              # 窗口程序，不弹黑色控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

# macOS 若要打成 .app，取消下面注释（需在 mac 上打包）：
# app = BUNDLE(
#     coll,
#     name=f"{APP_NAME}.app",
#     icon=ICON,
#     bundle_identifier="edu.tju.cagesim",
# )
