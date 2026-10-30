"""路径与资源定位。

打包成 exe（PyInstaller）后，只读资源位于 ``sys._MEIPASS``，
而用户数据（工程、结果）应放在 exe 所在目录或用户选择的目录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# UI/ 目录（源码运行时）
UI_DIR = Path(__file__).resolve().parent.parent
# 项目根目录（CagePython、网箱时域模拟2026-matlab 所在目录）
PROJECT_ROOT = UI_DIR.parent

FROZEN = getattr(sys, "frozen", False)


def resource_path(*parts: str) -> Path:
    """定位只读资源（图标、内置波面文件、字体等）。"""
    if FROZEN:
        base = Path(getattr(sys, "_MEIPASS", UI_DIR))
    else:
        base = UI_DIR
    return base.joinpath(*parts)


def app_dir() -> Path:
    """定位可写数据目录：打包后为 exe 所在目录，源码运行时为 UI/。"""
    if FROZEN:
        return Path(sys.executable).resolve().parent
    return UI_DIR


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# 默认数据目录
PROJECTS_DIR = app_dir() / "projects"
OUTPUT_DIR = app_dir() / "output"
LOGS_DIR = app_dir() / "logs"

# 内置资源目录（波面文件、WAMIT 文件默认位置）
DEFAULT_WAMIT_DIR = PROJECT_ROOT / "CagePython"
DEFAULT_WAVE_DIR = PROJECT_ROOT / "CagePython"


def open_in_explorer(path: Path) -> None:
    """在系统文件管理器中打开目录（跨平台）。"""
    path = Path(path)
    if not path.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')
