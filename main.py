"""程序入口。

运行::

    cd UI
    .venv/bin/python main.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# --------------------------------------------------------------------------- #
#  matplotlib 缓存目录
# --------------------------------------------------------------------------- #
# matplotlib 启动时会在「配置目录」里建字体缓存（fontlist-*.json）。
# 若该目录不可写，它会退回系统临时目录，而且**每次启动都重建缓存**，
# 表现为控制台反复出现：
#     Matplotlib created a temporary cache directory at /var/folders/...
#     Matplotlib is building the font cache; this may take a moment.
# 启动会慢十几秒，打包成 exe 后更容易遇到（用户 HOME 可能只读）。
#
# 这里固定到一个用户可写、跨次运行能复用的目录：
#   1. 优先 ~/.cagesim/mpl
#   2. 家目录不可写时，退到程序目录下的 .mplcache/
# 用 setdefault：用户若已设 MPLCONFIGDIR 环境变量则不覆盖。
# 必须在 import matplotlib 之前执行，所以放在所有 app 导入的前面。
def _set_mpl_cache_dir() -> None:
    candidates: list[Path] = []
    try:
        candidates.append(Path.home() / ".cagesim" / "mpl")
    except RuntimeError:
        pass                       # HOME 未设置
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".mplcache")
    else:
        candidates.append(Path(__file__).resolve().parent / ".mplcache")

    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        os.environ.setdefault("MPLCONFIGDIR", str(d))
        return


_set_mpl_cache_dir()

# 保证以脚本方式运行时能找到 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        from app.main import MainWindow
    except ImportError as exc:
        print("导入失败：", exc)
        return 1

    app = MainWindow()
    try:
        app.mainloop()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
