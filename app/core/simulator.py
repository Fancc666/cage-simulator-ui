"""仿真执行器。

把 ``CageEngine`` 放到后台线程里跑，通过 ``queue`` 把事件传回 UI 线程。

线程模型
--------
- 仿真跑在后台线程，UI 线程用 ``root.after`` 轮询队列，保证 Tkinter 不阻塞。
- ``state`` 是全局单例，所以同一时间只能跑一个仿真（本类已保证）。
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Project
from app.core.engine import CageEngine, EngineError, RunResult


# --------------------------------------------------------------------------- #
#  事件
# --------------------------------------------------------------------------- #
@dataclass
class Event:
    kind: str                     # log / stage / progress / done / error / result
    payload: dict = field(default_factory=dict)


STAGES = [
    "准备参数与入射波",
    "读取水动力系数",
    "装配质量阵与系泊",
    "时间推进",
    "后处理出图",
    "保存结果",
]


# --------------------------------------------------------------------------- #
#  运行器
# --------------------------------------------------------------------------- #
class SimulatorRunner:
    """在后台线程执行一次仿真。"""

    def __init__(self, project: Project, output_dir: Path,
                 program_dir: Path | None = None):
        self.project = project
        self.output_dir = Path(output_dir)
        self.program_dir = Path(program_dir) if program_dir else None
        self.events: queue.Queue[Event] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()

    # ---- 控制 ----
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag.set()
        self._pause_flag.clear()

    def pause(self) -> None:
        self._pause_flag.set()

    def resume(self) -> None:
        self._pause_flag.clear()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ---- 内部 ----
    def _emit(self, kind: str, **payload) -> None:
        self.events.put(Event(kind, payload))

    def _log(self, msg: str, level: str = "info") -> None:
        self._emit("log", msg=msg, level=level)

    def _on_progress(self, frac: float, text: str) -> None:
        """引擎回调：负数 frac 表示阶段事件。"""
        if frac < 0 and text.startswith("__stage__"):
            body = text[len("__stage__"):]
            idx_str, status = body.split(":", 1)
            self._emit("stage", index=int(idx_str), status=status)
            return
        while self._pause_flag.is_set() and not self._stop_flag.is_set():
            time.sleep(0.05)
        if self._stop_flag.is_set():
            raise _Stopped()
        self._emit("progress", frac=frac, text=text)

    def _run(self) -> None:
        try:
            if self.program_dir is None:
                raise EngineError("未设置程序目录（CagePython 文件夹）")
            engine = CageEngine(
                project=self.project,
                program_dir=self.program_dir,
                output_dir=self.output_dir,
                log=self._log,
                progress=self._on_progress,
            )
            result: RunResult = engine.run()
            self._emit("result", result=result)
        except _Stopped:
            self._log("用户中止", "warn")
        except EngineError as exc:
            self._emit("error", msg=str(exc), detail=exc.detail)
        except Exception as exc:  # noqa: BLE001
            import traceback
            self._emit("error", msg=f"{type(exc).__name__}: {exc}",
                       detail=traceback.format_exc())
        finally:
            self._emit("done", stopped=self._stop_flag.is_set())


class _Stopped(Exception):
    """内部用：用户点了停止。"""
