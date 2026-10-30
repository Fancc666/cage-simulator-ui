"""页面 ②：运行。

展示阶段进度、时间推进进度条、日志，提供开始 / 暂停 / 停止。
"""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app.core.simulator import STAGES, SimulatorRunner
from app.paths import OUTPUT_DIR, ensure_dir
from app.theme import Color, Fonts
from app.widgets import Card, LogView


class RunPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app = app
        self.runner: SimulatorRunner | None = None
        self._stage_labels: list[ttk.Label] = []
        self._start_time: float = 0.0

        # ---- 标题 ----
        head = ttk.Frame(self, padding=(18, 14, 18, 6))
        head.pack(fill="x")
        ttk.Label(head, text="运行", style="H1.TLabel").pack(side="left")
        self.case_label = ttk.Label(head, text="", style="Muted.TLabel")
        self.case_label.pack(side="left", padx=(12, 0))

        body = ttk.Frame(self, padding=(18, 0, 18, 0))
        body.pack(fill="both", expand=True)

        # ---- 阶段清单 ----
        card = Card(body, title="计算阶段")
        card.pack(fill="x", pady=(0, 12))
        for i, name in enumerate(STAGES):
            row = ttk.Frame(card.body, style="Card.TFrame")
            row.pack(fill="x", pady=2)
            icon = ttk.Label(row, text="○", style="Card.TLabel", width=3,
                             font=Fonts.get(11))
            icon.pack(side="left")
            label = ttk.Label(row, text=name, style="Card.TLabel")
            label.pack(side="left")
            self._stage_labels.append(icon)
            self._stage_icons = getattr(self, "_stage_icons", [])
            self._stage_icons.append(icon)

        # ---- 进度 ----
        prog_card = Card(body, title="进度")
        prog_card.pack(fill="x", pady=(0, 12))
        self.progress = ttk.Progressbar(prog_card.body, mode="determinate",
                                        maximum=100)
        self.progress.pack(fill="x")
        info = ttk.Frame(prog_card.body, style="Card.TFrame")
        info.pack(fill="x", pady=(6, 0))
        self.progress_text = ttk.Label(info, text="等待开始",
                                       style="CardMuted.TLabel")
        self.progress_text.pack(side="left")
        self.elapsed_text = ttk.Label(info, text="", style="CardMuted.TLabel")
        self.elapsed_text.pack(side="right")

        # ---- 日志 ----
        log_card = Card(body, title="日志")
        log_card.pack(fill="both", expand=True, pady=(0, 12))
        self.log_view = LogView(log_card.body, height=10)
        self.log_view.pack(fill="both", expand=True)

        # ---- 底部按钮 ----
        foot = ttk.Frame(self, padding=(18, 8, 18, 14))
        foot.pack(fill="x")
        self.btn_start = ttk.Button(foot, text="▶  开始运行",
                                    style="Primary.TButton",
                                    command=self._on_start)
        self.btn_start.pack(side="left")
        self.btn_pause = ttk.Button(foot, text="⏸  暂停", style="Ghost.TButton",
                                    command=self._on_pause, state="disabled")
        self.btn_pause.pack(side="left", padx=(8, 0))
        self.btn_stop = ttk.Button(foot, text="■  停止", style="Danger.TButton",
                                   command=self._on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        ttk.Button(foot, text="打开输出目录", style="Ghost.TButton",
                   command=self._open_output).pack(side="right")

        self._paused = False

    # ===================================================================== #
    #  生命周期
    # ===================================================================== #
    def on_show(self) -> None:
        """每次切到本页时刷新工况名。"""
        try:
            proj = self.app.project
            self.case_label.configure(
                text=f"{proj.name}  ·  {proj.wave.case_name()}")
        except Exception:  # noqa: BLE001
            pass

    # ===================================================================== #
    #  按钮
    # ===================================================================== #
    def _on_start(self) -> None:
        if self.runner and self.runner.is_running:
            return
        try:
            proj = self.app.input_page.collect()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        out_dir = ensure_dir(OUTPUT_DIR / proj.wave.case_name())
        self.log_view.clear()
        self._reset_stages()
        self.progress["value"] = 0
        self._paused = False
        self._start_time = time.time()

        self.runner = SimulatorRunner(proj, out_dir)
        self.runner.start()

        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸  暂停")
        self.btn_stop.configure(state="normal")
        self.app.log(f"开始运行：{proj.wave.case_name()}", "info")

        self.after(100, self._poll)

    def _on_pause(self) -> None:
        if not self.runner:
            return
        if self._paused:
            self.runner.resume()
            self._paused = False
            self.btn_pause.configure(text="⏸  暂停")
        else:
            self.runner.pause()
            self._paused = True
            self.btn_pause.configure(text="▶  继续")

    def _on_stop(self) -> None:
        if self.runner:
            self.runner.stop()
            self.app.log("请求停止…", "warn")

    def _open_output(self) -> None:
        from app.paths import open_in_explorer
        open_in_explorer(OUTPUT_DIR)

    # ===================================================================== #
    #  事件轮询
    # ===================================================================== #
    def _poll(self) -> None:
        if not self.runner:
            return
        finished = False
        try:
            while True:
                ev = self.runner.events.get_nowait()
                self._handle_event(ev)
                if ev.kind in ("done", "error"):
                    finished = True
        except Exception:  # queue.Empty
            pass

        if not finished:
            elapsed = time.time() - self._start_time
            self.elapsed_text.configure(text=f"已用时 {_fmt_duration(elapsed)}")
            self.after(100, self._poll)
        else:
            self._on_finished()

    def _handle_event(self, ev) -> None:
        if ev.kind == "log":
            self.log_view.append(ev.payload["msg"], ev.payload.get("level", "info"))
            self.app.log(ev.payload["msg"], ev.payload.get("level", "info"))
        elif ev.kind == "stage":
            idx = ev.payload["index"]
            status = ev.payload["status"]
            icon = self._stage_icons[idx]
            if status == "running":
                icon.configure(text="◐", foreground=Color.PRIMARY)
            elif status == "done":
                icon.configure(text="●", foreground=Color.OK)
        elif ev.kind == "progress":
            self.progress["value"] = ev.payload["frac"] * 100
            self.progress_text.configure(text=ev.payload.get("text", ""))
        elif ev.kind == "error":
            self.log_view.append(f"错误：{ev.payload['msg']}", "error")

    def _on_finished(self) -> None:
        elapsed = time.time() - self._start_time
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  暂停")
        self.btn_stop.configure(state="disabled")
        self.elapsed_text.configure(text=f"总用时 {_fmt_duration(elapsed)}")
        self.app.log("运行结束", "ok")
        self.app.show_page(2)   # 自动跳到结果页

    def _reset_stages(self) -> None:
        for icon in self._stage_icons:
            icon.configure(text="○", foreground=Color.TEXT_MUTED)


def _fmt_duration(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
