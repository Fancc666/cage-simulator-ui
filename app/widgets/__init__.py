"""通用小部件。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Sequence

from app.theme import Color, Fonts


class Card(ttk.Frame):
    """带标题的白色卡片容器。

    用法::

        card = Card(parent, title="波浪工况")
        body = card.body          # 往这里放控件
    """

    def __init__(self, master, title: str = "", subtitle: str = "", **kw):
        super().__init__(master, style="Card.TFrame", padding=0, **kw)

        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", padx=14, pady=(12, 0))
        if title:
            ttk.Label(header, text=title, style="CardH2.TLabel").pack(side="left")
        if subtitle:
            ttk.Label(header, text=subtitle, style="CardMuted.TLabel").pack(
                side="left", padx=(10, 0))

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=14, pady=(8, 0))

        self.body = ttk.Frame(self, style="Card.TFrame")
        self.body.pack(fill="both", expand=True, padx=14, pady=(10, 12))


class Field(ttk.Frame):
    """一行「标签 + 输入控件」，可选单位后缀与提示。"""

    def __init__(self, master, label: str, var: tk.Variable,
                 unit: str = "", width: int = 14, hint: str = "",
                 row: int = 0, col: int = 0, **kw):
        super().__init__(master, style="Card.TFrame", **kw)
        self.grid(row=row, column=col, sticky="w", padx=(0, 18), pady=4)

        ttk.Label(self, text=label, style="Card.TLabel", width=12,
                  anchor="w").pack(side="left")
        self.entry = ttk.Entry(self, textvariable=var, width=width)
        self.entry.pack(side="left")
        if unit:
            ttk.Label(self, text=unit, style="CardMuted.TLabel").pack(
                side="left", padx=(4, 0))
        if hint:
            ttk.Label(self, text=hint, style="CardMuted.TLabel").pack(
                side="left", padx=(6, 0))


class StatBadge(ttk.Frame):
    """状态徽标：● 已找到 / ● 缺失 / ● 未检查。"""

    def __init__(self, master, text: str = "未检查", state: str = "unknown"):
        super().__init__(master, style="Card.TFrame")
        self.dot = ttk.Label(self, text="●", style="Card.TLabel")
        self.dot.pack(side="left")
        self.text = ttk.Label(self, text=text, style="CardMuted.TLabel")
        self.text.pack(side="left", padx=(4, 0))
        self.set(text, state)

    def set(self, text: str, state: str = "unknown") -> None:
        colors = {"ok": Color.OK, "missing": Color.MISSING,
                  "unknown": Color.UNKNOWN, "warn": Color.WARNING}
        self.dot.configure(foreground=colors.get(state, Color.UNKNOWN))
        self.text.configure(text=text)


class FileRow(ttk.Frame):
    """「文件名 + 说明 + 状态徽标」一行，用于 WAMIT 文件检查表。"""

    def __init__(self, master, filename: str, desc: str):
        super().__init__(master, style="Card.TFrame")
        self.filename = filename
        ttk.Label(self, text=filename, style="Card.TLabel", width=16,
                  anchor="w").pack(side="left")
        ttk.Label(self, text=desc, style="CardMuted.TLabel", width=22,
                  anchor="w").pack(side="left")
        self.badge = StatBadge(self)
        self.badge.pack(side="left", padx=(8, 0))
        self.detail = ttk.Label(self, text="", style="CardMuted.TLabel")
        self.detail.pack(side="left", padx=(10, 0))

    def set_state(self, text: str, state: str, detail: str = "") -> None:
        self.badge.set(text, state)
        self.detail.configure(text=detail)


class ScrollFrame(ttk.Frame):
    """可垂直滚动的容器，内容放进 ``.inner``。"""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg=Color.BG, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")

        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _on_mousewheel(self, event):
        # 只在鼠标位于本容器上时滚动
        widget = self.winfo_containing(event.x_root, event.y_root)
        parent = widget
        while parent is not None:
            if parent is self:
                delta = -1 * (event.delta // 120) if event.delta else 0
                if delta:
                    self.canvas.yview_scroll(int(delta), "units")
                return
            parent = getattr(parent, "master", None)


class LogView(ttk.Frame):
    """深色日志窗口。"""

    def __init__(self, master, height: int = 12):
        super().__init__(master)
        self.text = tk.Text(self, height=height, wrap="none",
                            bg=Color.LOG_BG, fg=Color.LOG_FG,
                            insertbackground=Color.LOG_FG,
                            font=(Fonts.family, 9),
                            relief="flat", padx=10, pady=8,
                            state="disabled")
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=ybar.set)
        self.text.pack(side="left", fill="both", expand=True)
        ybar.pack(side="right", fill="y")

        self.text.tag_configure("info", foreground="#93c5fd")
        self.text.tag_configure("ok", foreground="#86efac")
        self.text.tag_configure("warn", foreground="#fcd34d")
        self.text.tag_configure("error", foreground="#fca5a5")

    def append(self, msg: str, level: str = "info") -> None:
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class Stepper(ttk.Frame):
    """顶部步骤条：① 输入 → ② 运行 → ③ 结果。"""

    def __init__(self, master, steps: Sequence[str],
                 on_click: Callable[[int], None] | None = None):
        super().__init__(master)
        self._labels: list[tk.Label] = []
        self._on_click = on_click

        for i, name in enumerate(steps):
            lbl = tk.Label(self, text=f"{i + 1}  {name}",
                           font=Fonts.get(10, "bold"),
                           bg=Color.BG, fg=Color.TEXT_MUTED,
                           padx=14, pady=6, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda _e, idx=i: self._click(idx))
            self._labels.append(lbl)
            if i < len(steps) - 1:
                tk.Label(self, text="›", bg=Color.BG, fg=Color.BORDER,
                         font=Fonts.get(14)).pack(side="left")

        self.set_current(0)

    def _click(self, idx: int) -> None:
        if self._on_click:
            self._on_click(idx)

    def set_current(self, idx: int) -> None:
        for i, lbl in enumerate(self._labels):
            if i == idx:
                lbl.configure(bg=Color.PRIMARY, fg=Color.TEXT_INVERSE)
            else:
                lbl.configure(bg=Color.BG, fg=Color.TEXT_MUTED)


def labeled_separator(master, text: str) -> ttk.Frame:
    """带文字的分隔线。"""
    frame = ttk.Frame(master)
    ttk.Label(frame, text=text, style="CardMuted.TLabel").pack(side="left")
    ttk.Separator(frame, orient="horizontal").pack(
        side="left", fill="x", expand=True, padx=(8, 0))
    return frame
