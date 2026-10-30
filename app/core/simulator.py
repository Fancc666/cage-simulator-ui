"""仿真执行器（骨架版）。

当前只做「流程演示」：按阶段推进进度、写日志、生成占位结果文件，
用于验证 UI 的交互是否顺畅。后续把 ``_run_stages`` 里的
``time.sleep`` 换成真正的计算调用即可。

线程模型
--------
仿真跑在后台线程里，通过 ``queue.Queue`` 把事件传回 UI 线程，
UI 线程用 ``root.after`` 轮询，保证 Tkinter 不被阻塞。
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.config import Project


# --------------------------------------------------------------------------- #
#  事件
# --------------------------------------------------------------------------- #
@dataclass
class Event:
    kind: str                     # log / stage / progress / done / error
    payload: dict = field(default_factory=dict)


STAGES = [
    "准备参数",
    "读取水动力系数",
    "计算一阶/二阶激振力",
    "时间推进",
    "后处理出图",
    "保存结果",
]


# --------------------------------------------------------------------------- #
#  运行器
# --------------------------------------------------------------------------- #
class SimulatorRunner:
    """在后台线程执行一次仿真。"""

    def __init__(self, project: Project, output_dir: Path):
        self.project = project
        self.output_dir = Path(output_dir)
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

    def _check_stop(self) -> bool:
        while self._pause_flag.is_set() and not self._stop_flag.is_set():
            time.sleep(0.05)
        return self._stop_flag.is_set()

    def _run(self) -> None:
        try:
            self._run_stages()
        except Exception as exc:  # noqa: BLE001
            self._emit("error", msg=str(exc))
        finally:
            self._emit("done", stopped=self._stop_flag.is_set())

    def _run_stages(self) -> None:
        """骨架：按阶段推进。真实计算替换这里的内容。"""
        proj = self.project
        wave = proj.wave

        # 估算总步数（真实计算里由波面文件长度决定）
        if wave.mode == "file":
            total_steps = 10000
        elif wave.mode == "irregular":
            total_steps = int(wave.duration / wave.dt)
        else:
            total_steps = 20000

        self._log(f"工程：{proj.name}")
        self._log(f"工况：{wave.case_name()}")
        self._log(f"时间步 dt={wave.dt}s，总步数 {total_steps}")

        # ---- 阶段 1：准备参数 ----
        self._emit("stage", index=0, status="running")
        time.sleep(0.4)
        self._log("Finish Read Parameter", "ok")
        self._emit("stage", index=0, status="done")
        if self._check_stop():
            return

        # ---- 阶段 2：读取水动力 ----
        self._emit("stage", index=1, status="running")
        files = proj.hydro.file_paths()
        found = sum(1 for _, _, p in files if p.exists())
        time.sleep(0.6)
        self._log(f"水动力文件：{found}/{len(files)} 个已找到", "ok")
        self._emit("stage", index=1, status="done")
        if self._check_stop():
            return

        # ---- 阶段 3：激振力 ----
        self._emit("stage", index=2, status="running")
        time.sleep(0.5)
        self._log("一阶/二阶激振力计算完成", "ok")
        self._emit("stage", index=2, status="done")
        if self._check_stop():
            return

        # ---- 阶段 4：时间推进 ----
        self._emit("stage", index=3, status="running")
        chunk = max(1, total_steps // 100)
        for step in range(0, total_steps + 1, chunk):
            if self._check_stop():
                self._log("用户中止", "warn")
                return
            if self._pause_flag.is_set():
                self._log("已暂停", "warn")
                if self._check_stop():
                    return
                self._log("继续运行", "info")
            frac = min(1.0, step / total_steps)
            self._emit("progress", frac=frac,
                       text=f"t = {step * wave.dt:.1f} s / {total_steps * wave.dt:.0f} s")
            time.sleep(0.02)
        self._emit("progress", frac=1.0, text="时间推进完成")
        self._log("时间推进完成", "ok")
        self._emit("stage", index=3, status="done")

        # ---- 阶段 5：后处理 ----
        self._emit("stage", index=4, status="running")
        time.sleep(0.6)
        self._log("生成 11 张图（占位）", "ok")
        self._emit("stage", index=4, status="done")

        # ---- 阶段 6：保存 ----
        self._emit("stage", index=5, status="running")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "README_placeholder.txt").write_text(
            "骨架版本：此处应生成 *_TSR.mat / *_TSR.npz / *_统计结果.txt / fig*.png\n",
            encoding="utf-8",
        )
        time.sleep(0.3)
        self._log(f"结果已保存到：{self.output_dir}", "ok")
        self._emit("stage", index=5, status="done")
