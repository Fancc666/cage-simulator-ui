"""页面 ③：结果。

左侧工况列表，右侧统计摘要 + 图片缩略图 + 交互曲线（骨架占位）。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from app.paths import OUTPUT_DIR, open_in_explorer
from app.theme import Color, Fonts
from app.widgets import Card


class ResultPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app = app

        # ---- 标题 ----
        head = ttk.Frame(self, padding=(18, 14, 18, 6))
        head.pack(fill="x")
        ttk.Label(head, text="结果", style="H1.TLabel").pack(side="left")
        ttk.Button(head, text="刷新", style="Ghost.TButton",
                   command=self.refresh).pack(side="right")
        ttk.Button(head, text="打开输出目录", style="Ghost.TButton",
                   command=lambda: open_in_explorer(OUTPUT_DIR)).pack(
            side="right", padx=(0, 8))

        # ---- 主体：左列表 + 右内容 ----
        body = ttk.Frame(self, padding=(18, 0, 18, 14))
        body.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 左：工况列表
        left = ttk.Frame(paned, width=240)
        paned.add(left, weight=0)
        ttk.Label(left, text="已完成的工况", style="H2.TLabel").pack(
            anchor="w", pady=(0, 6))
        self.case_list = tk.Listbox(
            left, activestyle="none", exportselection=False,
            font=Fonts.get(10), relief="solid", borderwidth=1,
            highlightthickness=0, selectbackground=Color.PRIMARY,
            selectforeground=Color.TEXT_INVERSE)
        self.case_list.pack(fill="both", expand=True)
        self.case_list.bind("<<ListboxSelect>>", self._on_select)

        # 右：内容
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        # 统计摘要
        stat_card = Card(right, title="统计摘要")
        stat_card.pack(fill="x", pady=(0, 12))
        self.stat_label = ttk.Label(
            stat_card.body,
            text="选择一个工况查看统计结果。\n\n"
                 "（骨架版本：真实统计来自 *_统计结果.txt）",
            style="CardMuted.TLabel", justify="left")
        self.stat_label.pack(anchor="w")

        # 图片缩略图
        fig_card = Card(right, title="结果图片")
        fig_card.pack(fill="both", expand=True, pady=(0, 12))
        self.fig_grid = ttk.Frame(fig_card.body, style="Card.TFrame")
        self.fig_grid.pack(fill="both", expand=True)
        self._fig_placeholder = ttk.Label(
            self.fig_grid,
            text="（骨架版本：此处显示 fig171 / fig173 / fig188 … 的缩略图网格）",
            style="CardMuted.TLabel")
        self._fig_placeholder.pack(anchor="w")

        # 交互曲线
        curve_card = Card(right, title="时程曲线")
        curve_card.pack(fill="x")
        row = ttk.Frame(curve_card.body, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="自由度", style="Card.TLabel").pack(side="left")
        self.var_dof = tk.StringVar(value="纵荡")
        ttk.Combobox(row, textvariable=self.var_dof, width=10,
                     values=["纵荡", "横荡", "垂荡", "横摇", "纵摇", "艏摇"],
                     state="readonly").pack(side="left", padx=(6, 16))
        ttk.Label(row, text="缆绳", style="Card.TLabel").pack(side="left")
        self.var_line = tk.StringVar(value="L1")
        ttk.Combobox(row, textvariable=self.var_line, width=8,
                     values=["L1", "L2", "R1", "R2"],
                     state="readonly").pack(side="left", padx=(6, 0))
        ttk.Label(curve_card.body,
                  text="（骨架版本：此处嵌入 matplotlib 交互曲线）",
                  style="CardMuted.TLabel").pack(anchor="w", pady=(8, 0))

        self.refresh()

    # ===================================================================== #
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        """扫描输出目录，列出已有工况。"""
        self.case_list.delete(0, "end")
        if not OUTPUT_DIR.exists():
            self.case_list.insert("end", "（暂无结果）")
            return
        cases = sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_dir())
        if not cases:
            self.case_list.insert("end", "（暂无结果）")
            return
        for name in cases:
            self.case_list.insert("end", name)

    def _on_select(self, _event=None) -> None:
        sel = self.case_list.curselection()
        if not sel:
            return
        name = self.case_list.get(sel[0])
        folder = OUTPUT_DIR / name
        files = list(folder.glob("*")) if folder.exists() else []
        self.stat_label.configure(
            text=f"工况：{name}\n"
                 f"目录：{folder}\n"
                 f"文件数：{len(files)}\n\n"
                 f"（骨架版本：真实统计来自 *_统计结果.txt）")
