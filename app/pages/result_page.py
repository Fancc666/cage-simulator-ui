"""页面 ③：结果。

左侧工况列表，右侧统计摘要 + 图片缩略图 + 交互曲线。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from app.paths import OUTPUT_DIR, open_in_explorer
from app.theme import Color, FontSize, Fonts
from app.widgets import Card


# 图片编号 → 中文标题
FIG_TITLES = {
    171: "运动响应原始时程",
    173: "系泊力原始时程",
    188: "运动响应谱",
    189: "系泊力谱",
    191: "运动滤波前后对比",
    193: "系泊力滤波前后对比",
    200: "入射波面（生成）",
    203: "入射波面（外部文件）",
    1: "入射波浪谱",
    1001: "入射波波幅谱",
    4: "时域一阶/二阶激振力",
    71: "JONSWAP 目标谱",
}


class ResultPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app = app
        self._result = None
        self._thumb_refs: list = []

        # ---- 标题 ----
        head = ttk.Frame(self, padding=(20, 16, 20, 8))
        head.pack(fill="x")
        ttk.Label(head, text="结果", style="H1.TLabel").pack(side="left")
        ttk.Button(head, text="刷新", style="Ghost.TButton",
                   command=self.refresh).pack(side="right")
        ttk.Button(head, text="打开输出目录", style="Ghost.TButton",
                   command=lambda: open_in_explorer(OUTPUT_DIR)).pack(
            side="right", padx=(0, 8))

        # ---- 主体：左列表 + 右内容 ----
        body = ttk.Frame(self, padding=(20, 0, 20, 16))
        body.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 左：工况列表
        left = ttk.Frame(paned, width=250)
        paned.add(left, weight=0)
        ttk.Label(left, text="已完成的工况", style="H2.TLabel").pack(
            anchor="w", pady=(0, 8))
        self.case_list = tk.Listbox(
            left, activestyle="none", exportselection=False,
            font=Fonts.get(FontSize.BASE), relief="flat", borderwidth=0,
            highlightthickness=0, selectbackground=Color.PRIMARY,
            selectforeground=Color.TEXT_INVERSE)
        self.case_list.pack(fill="both", expand=True)
        self.case_list.bind("<<ListboxSelect>>", self._on_select)

        # 右：内容
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        # 统计摘要
        stat_card = Card(right, title="统计摘要")
        stat_card.pack(fill="x", pady=(0, 14))
        self.stat_label = ttk.Label(
            stat_card.body,
            text="选择一个工况查看统计结果。",
            style="CardMuted.TLabel", justify="left")
        self.stat_label.pack(anchor="w")

        # 图片缩略图
        fig_card = Card(right, title="结果图片")
        fig_card.pack(fill="both", expand=True, pady=(0, 14))
        self.fig_grid = ttk.Frame(fig_card.body, style="Card.TFrame")
        self.fig_grid.pack(fill="both", expand=True)
        self._fig_placeholder = ttk.Label(
            self.fig_grid,
            text="运行完成后，这里显示 fig171 / fig173 / fig188 … 的缩略图。",
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
                  text="（曲线绘制将在下一步接入）",
                  style="CardMuted.TLabel").pack(anchor="w", pady=(8, 0))

        self.refresh()

    # ===================================================================== #
    def on_show(self) -> None:
        self.refresh()

    def set_result(self, result) -> None:
        """接收运行页传来的 RunResult。"""
        self._result = result
        self.refresh()
        self._show_result(result)

    def refresh(self) -> None:
        """扫描输出目录，列出已有工况。"""
        current = self._selected_case()
        self.case_list.delete(0, "end")
        cases = []
        if OUTPUT_DIR.exists():
            cases = sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_dir())
        if not cases:
            self.case_list.insert("end", "（暂无结果）")
            return
        for name in cases:
            self.case_list.insert("end", name)
        # 尽量保持原选中项
        if current in cases:
            idx = cases.index(current)
            self.case_list.selection_set(idx)
            self.case_list.see(idx)

    def _selected_case(self) -> str | None:
        sel = self.case_list.curselection()
        if not sel:
            return None
        text = self.case_list.get(sel[0])
        return None if text.startswith("（") else text

    def _on_select(self, _event=None) -> None:
        name = self._selected_case()
        if not name:
            return
        folder = OUTPUT_DIR / name
        if self._result is not None and self._result.case_name == name:
            self._show_result(self._result)
            return
        # 从磁盘加载已有结果
        npz = folder / f"{name}_TSR.npz"
        if npz.exists():
            try:
                import numpy as np
                data = np.load(npz, allow_pickle=True)
                self.stat_label.configure(
                    text=f"工况：{name}\n"
                         f"时长：{float(data['time'][-1]):.1f} s\n"
                         f"初始系泊力：{float(data['mooring'][0, 0]):.2f} N / 缆\n"
                         f"目录：{folder}")
            except Exception as exc:  # noqa: BLE001
                self.stat_label.configure(text=f"读取失败：{exc}")
        else:
            files = list(folder.glob("*")) if folder.exists() else []
            self.stat_label.configure(
                text=f"工况：{name}\n目录：{folder}\n文件数：{len(files)}")
        self._show_figures(folder)

    # ===================================================================== #
    def _show_result(self, result) -> None:
        """展示 RunResult 的统计与图片。"""
        import numpy as np

        dof = ["纵荡", "横荡", "垂荡", "横摇", "纵摇", "艏摇"]
        lines = [
            f"工况：{result.case_name}",
            f"时长：{result.time[-1]:.1f} s（{len(result.time)} 步）",
            f"初始系泊力：{result.mooring[0, 0]:.2f} N / 缆",
            "",
            "运动响应（波频分量特征值）",
        ]
        for j in range(6):
            h13, h110, hmax = result.stats_motion[6 + j, :]
            unit = "m" if j < 3 else "rad"
            lines.append(f"  {dof[j]}：H1/3={h13:.4g}  H1/10={h110:.4g}  "
                         f"Hmax={hmax:.4g} {unit}")
        lines.append("")
        lines.append("系泊缆张力（全时历极值）")
        for i, name in enumerate(["L1", "L2", "R1", "R2"]):
            lines.append(f"  {name}：最大 {result.momax[6 + i]:.1f} N  "
                         f"最小 {result.momax[10 + i]:.1f} N")
        self.stat_label.configure(text="\n".join(lines))

        self._show_figures(result.output_dir)

    def _show_figures(self, folder: Path) -> None:
        """在网格里显示缩略图。"""
        for w in self.fig_grid.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        if not folder.exists():
            ttk.Label(self.fig_grid, text="目录不存在",
                      style="CardMuted.TLabel").pack(anchor="w")
            return

        pngs = sorted(folder.glob("fig*.png"))
        k66 = folder / "K66-0.png"
        if k66.exists():
            pngs.append(k66)
        if not pngs:
            ttk.Label(self.fig_grid, text="暂无图片",
                      style="CardMuted.TLabel").pack(anchor="w")
            return

        try:
            from PIL import Image, ImageTk
        except ImportError:
            ttk.Label(self.fig_grid, text="缺少 Pillow，无法显示缩略图",
                      style="CardMuted.TLabel").pack(anchor="w")
            return

        cols = 4
        for i, path in enumerate(pngs):
            try:
                img = Image.open(path)
                img.thumbnail((220, 140))
                photo = ImageTk.PhotoImage(img)
            except Exception:  # noqa: BLE001
                continue
            self._thumb_refs.append(photo)

            cell = ttk.Frame(self.fig_grid, style="Card.TFrame")
            cell.grid(row=i // cols, column=i % cols, padx=6, pady=6,
                      sticky="nw")
            lbl = ttk.Label(cell, image=photo, style="Card.TLabel")
            lbl.pack()
            num = path.stem.replace("fig", "").replace("K66-0", "K66")
            try:
                title = FIG_TITLES.get(int(num), path.stem)
            except ValueError:
                title = "辐射迟滞函数 K66"
            ttk.Label(cell, text=title, style="CardMuted.TLabel").pack(
                anchor="w", pady=(2, 0))
