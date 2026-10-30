"""程序入口。

运行::

    cd UI
    .venv/bin/python main.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

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
