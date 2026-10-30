"""页面 ①：输入。

三块内容：
  - 水动力系数（WAMIT 6 个文件，带存在性检查）
  - 波浪工况（规则波 / JONSWAP / 外部波面文件，三选一）
  - 系泊系统（缆绳属性 + 导缆孔表格，默认收起）
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.core.config import Project
from app.paths import DEFAULT_WAMIT_DIR, DEFAULT_WAVE_DIR
from app.theme import Color, FontSize, Fonts
from app.widgets import Card, Field, FileRow, ScrollFrame


class InputPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app = app
        self.project: Project = app.project

        # ---- 顶部标题 ----
        head = ttk.Frame(self, padding=(20, 16, 20, 8))
        head.pack(fill="x")
        ttk.Label(head, text="输入", style="H1.TLabel").pack(side="left")
        ttk.Label(head, text="水动力系数 + 波浪工况 + 系泊布置",
                  style="Muted.TLabel").pack(side="left", padx=(12, 0))

        # ---- 可滚动内容 ----
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        body = scroll.inner

        self._build_hydro(body)
        self._build_wave(body)
        self._build_mooring(body)

        # ---- 底部按钮 ----
        foot = ttk.Frame(self, padding=(20, 10, 20, 16))
        foot.pack(fill="x")
        ttk.Button(foot, text="保存工程", style="Ghost.TButton",
                   command=self._on_save).pack(side="left")
        ttk.Button(foot, text="加载工程", style="Ghost.TButton",
                   command=self._on_load).pack(side="left", padx=(8, 0))
        ttk.Button(foot, text="下一步：运行  →", style="Primary.TButton",
                   command=lambda: self.app.show_page(1)).pack(side="right")

        self._sync_case_name()

    # ===================================================================== #
    #  水动力
    # ===================================================================== #
    def _build_hydro(self, parent) -> None:
        card = Card(parent, title="① 水动力系数",
                    subtitle="WAMIT 输出，一次算好反复使用")
        card.pack(fill="x", pady=(0, 14))
        b = card.body

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="文件目录", style="Card.TLabel", width=12,
                  anchor="w").pack(side="left")
        self.var_hydro_dir = tk.StringVar(
            value=self.project.hydro.folder or str(DEFAULT_WAMIT_DIR))
        ttk.Entry(row, textvariable=self.var_hydro_dir).pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="浏览…", command=self._pick_hydro_dir).pack(
            side="left", padx=(8, 0))

        row2 = ttk.Frame(b, style="Card.TFrame")
        row2.pack(fill="x", pady=(0, 10))
        ttk.Label(row2, text="文件前缀", style="Card.TLabel", width=12,
                  anchor="w").pack(side="left")
        self.var_prefix = tk.StringVar(value=self.project.hydro.prefix)
        ttk.Entry(row2, textvariable=self.var_prefix, width=20).pack(side="left")
        ttk.Button(row2, text="检查文件", command=self._check_hydro).pack(
            side="left", padx=(10, 0))
        self.hydro_summary = ttk.Label(row2, text="", style="CardMuted.TLabel")
        self.hydro_summary.pack(side="left", padx=(12, 0))

        # 文件清单
        self.file_rows: dict[str, FileRow] = {}
        listbox = ttk.Frame(b, style="Card.TFrame")
        listbox.pack(fill="x")
        for suffix, desc in self.project.hydro.REQUIRED_FILES:
            fr = FileRow(listbox, f"{self.project.hydro.prefix}{suffix}", desc)
            fr.pack(fill="x", pady=1)
            self.file_rows[suffix] = fr

        # 参数
        params = ttk.Frame(b, style="Card.TFrame")
        params.pack(fill="x", pady=(10, 0))
        self.var_hbot = tk.StringVar(value=str(self.project.hydro.hbot))
        self.var_rho = tk.StringVar(value=str(self.project.hydro.rho))
        Field(params, "水深 hbot", self.var_hbot, unit="m", row=0, col=0)
        Field(params, "流体密度 ρ", self.var_rho, unit="kg/m³", row=0, col=1)

        # 自由度
        dof_row = ttk.Frame(b, style="Card.TFrame")
        dof_row.pack(fill="x", pady=(6, 0))
        ttk.Label(dof_row, text="自由度", style="Card.TLabel", width=12,
                  anchor="w").pack(side="left")
        self.dof_vars: list[tk.IntVar] = []
        names = ["纵荡", "横荡", "垂荡", "横摇", "纵摇", "艏摇"]
        for i, name in enumerate(names):
            v = tk.IntVar(value=self.project.hydro.imode[i])
            ttk.Checkbutton(dof_row, text=name, variable=v,
                            style="Card.TCheckbutton").pack(side="left",
                                                            padx=(0, 10))
            self.dof_vars.append(v)

        self._check_hydro()

    def _pick_hydro_dir(self) -> None:
        path = filedialog.askdirectory(
            title="选择 WAMIT 文件所在目录",
            initialdir=self.var_hydro_dir.get() or str(DEFAULT_WAMIT_DIR))
        if path:
            self.var_hydro_dir.set(path)
            self._check_hydro()

    def _check_hydro(self) -> None:
        folder = Path(self.var_hydro_dir.get())
        prefix = self.var_prefix.get().strip() or "WAMIT_5S"
        found = 0
        for suffix, desc in self.project.hydro.REQUIRED_FILES:
            path = folder / f"{prefix}{suffix}"
            row = self.file_rows[suffix]
            row.filename = path.name
            if path.exists():
                size = path.stat().st_size
                row.set_state("已找到", "ok", _human_size(size))
                found += 1
            else:
                row.set_state("缺失", "missing", "")
        total = len(self.project.hydro.REQUIRED_FILES)
        self.hydro_summary.configure(
            text=f"{found}/{total} 个文件就绪",
            foreground=Color.OK if found == total else Color.MISSING)

    # ===================================================================== #
    #  波浪
    # ===================================================================== #
    def _build_wave(self, parent) -> None:
        card = Card(parent, title="② 波浪工况", subtitle="三种波型三选一")
        card.pack(fill="x", pady=(0, 14))
        b = card.body

        self.var_wave_mode = tk.StringVar(value=self.project.wave.mode)
        mode_row = ttk.Frame(b, style="Card.TFrame")
        mode_row.pack(fill="x", pady=(0, 8))
        for value, label in [("regular", "规则波"),
                             ("irregular", "不规则波 (JONSWAP)"),
                             ("file", "外部波面文件")]:
            ttk.Radiobutton(mode_row, text=label, value=value,
                            variable=self.var_wave_mode,
                            style="Card.TRadiobutton",
                            command=self._switch_wave_mode).pack(
                side="left", padx=(0, 18))

        # 三个参数面板，切换显示
        self.wave_panels: dict[str, ttk.Frame] = {}

        # ---- 规则波 ----
        p = ttk.Frame(b, style="Card.TFrame")
        self.var_reg_h = tk.StringVar(value=str(self.project.wave.regular_h))
        self.var_reg_t = tk.StringVar(value=str(self.project.wave.regular_t))
        self.var_ramp = tk.IntVar(value=int(self.project.wave.ramp))
        Field(p, "波高 H", self.var_reg_h, unit="m", row=0, col=0)
        Field(p, "周期 T", self.var_reg_t, unit="s", row=0, col=1)
        ttk.Checkbutton(p, text="加渐入 / 渐出段（100 s）",
                        variable=self.var_ramp,
                        style="Card.TCheckbutton").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.wave_panels["regular"] = p

        # ---- JONSWAP ----
        p = ttk.Frame(b, style="Card.TFrame")
        w = self.project.wave
        self.var_hs = tk.StringVar(value=str(w.hs))
        self.var_tp = tk.StringVar(value=str(w.tp))
        self.var_gamma = tk.StringVar(value=str(w.gamma))
        self.var_duration = tk.StringVar(value=str(w.duration))
        self.var_seed = tk.StringVar(value=str(w.seed))
        Field(p, "有义波高 Hs", self.var_hs, unit="m", row=0, col=0)
        Field(p, "谱峰周期 Tp", self.var_tp, unit="s", row=0, col=1)
        Field(p, "谱峰因子 γ", self.var_gamma, row=1, col=0)
        Field(p, "模拟时长", self.var_duration, unit="s", row=1, col=1)
        Field(p, "随机种子", self.var_seed, row=2, col=0,
              hint="5489 = MATLAB 默认")
        self.wave_panels["irregular"] = p

        # ---- 外部文件 ----
        p = ttk.Frame(b, style="Card.TFrame")
        file_row = ttk.Frame(p, style="Card.TFrame")
        file_row.pack(fill="x")
        ttk.Label(file_row, text="波面文件", style="Card.TLabel",
                  width=12, anchor="w").pack(side="left")
        self.var_wave_file = tk.StringVar(value=self.project.wave.wave_file)
        ttk.Entry(file_row, textvariable=self.var_wave_file).pack(
            side="left", fill="x", expand=True)
        ttk.Button(file_row, text="浏览…", command=self._pick_wave_file).pack(
            side="left", padx=(8, 0))
        self.wave_info = ttk.Label(p, text="", style="CardMuted.TLabel")
        self.wave_info.pack(anchor="w", pady=(6, 0))
        self.wave_panels["file"] = p

        # ---- 通用参数 ----
        common = ttk.Frame(b, style="Card.TFrame")
        common.pack(fill="x", pady=(10, 0))
        self.var_dt = tk.StringVar(value=str(self.project.wave.dt))
        self.var_numhum = tk.StringVar(value=str(self.project.wave.numhum))
        Field(common, "时间步 dt", self.var_dt, unit="s", row=0, col=0)
        Field(common, "谱平滑窗", self.var_numhum, row=0, col=1)

        out_row = ttk.Frame(b, style="Card.TFrame")
        out_row.pack(fill="x", pady=(6, 0))
        ttk.Label(out_row, text="输出目录名", style="Card.TLabel",
                  width=12, anchor="w").pack(side="left")
        self.case_name_label = ttk.Label(out_row, text="", style="Card.TLabel",
                                         font=Fonts.get(FontSize.BASE, "bold"))
        self.case_name_label.pack(side="left")

        self._switch_wave_mode()

    def _switch_wave_mode(self) -> None:
        for name, panel in self.wave_panels.items():
            panel.pack_forget()
        self.wave_panels[self.var_wave_mode.get()].pack(fill="x")
        self._sync_case_name()

    def _pick_wave_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择波面文件",
            initialdir=str(DEFAULT_WAVE_DIR),
            filetypes=[("波面文件", "*.txt *.dat"), ("所有文件", "*.*")])
        if path:
            self.var_wave_file.set(path)
            self._inspect_wave_file(path)

    def _inspect_wave_file(self, path: str) -> None:
        """读取波面文件头部，显示步数与时长。"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            if len(lines) < 5:
                raise ValueError("文件行数不足")
            header = [float(t) for t in lines[1].split()]
            dt = header[1]
            n = len(lines) - 4
            self.wave_info.configure(
                text=f"解析结果：{n} 步 × {dt} s = {n * dt:.0f} s，"
                     f"{int(header[2])} 个浪向",
                foreground=Color.OK)
        except Exception as exc:  # noqa: BLE001
            self.wave_info.configure(text=f"解析失败：{exc}",
                                     foreground=Color.MISSING)

    def _sync_case_name(self) -> None:
        mode = self.var_wave_mode.get()
        try:
            if mode == "regular":
                name = f"RegularH={self.var_reg_h.get()}T={self.var_reg_t.get()}"
            elif mode == "irregular":
                name = f"IrregularHs={self.var_hs.get()}Tp={self.var_tp.get()}"
            else:
                stem = Path(self.var_wave_file.get()).stem or "wave_file"
                name = stem
        except Exception:  # noqa: BLE001
            name = "—"
        self.case_name_label.configure(text=name)

    # ===================================================================== #
    #  系泊
    # ===================================================================== #
    def _build_mooring(self, parent) -> None:
        card = Card(parent, title="③ 系泊系统",
                    subtitle="一般用默认值，高级用户再展开")
        card.pack(fill="x", pady=(0, 14))
        b = card.body

        # 折叠开关
        self.moor_open = tk.BooleanVar(value=False)
        ttk.Checkbutton(b, text="显示系泊详细参数", variable=self.moor_open,
                        style="Card.TCheckbutton",
                        command=self._toggle_mooring).pack(anchor="w")

        self.moor_body = ttk.Frame(b, style="Card.TFrame")

        # 缆绳属性
        m = self.project.mooring
        props = ttk.Frame(self.moor_body, style="Card.TFrame")
        props.pack(fill="x", pady=(8, 0))
        self.var_w = tk.StringVar(value=str(m.wet_weight))
        self.var_ea = tk.StringVar(value=f"{m.ea:.4g}")
        self.var_depth = tk.StringVar(value=str(m.depth))
        self.var_length = tk.StringVar(value=str(m.length))
        self.var_pt_min = tk.StringVar(value=str(m.pretension_min))
        self.var_pt_max = tk.StringVar(value=str(m.pretension_max))
        self.var_pt_step = tk.StringVar(value=str(m.pretension_step))
        Field(props, "湿重 w", self.var_w, unit="N/m", row=0, col=0)
        Field(props, "轴向刚度 EA", self.var_ea, unit="N", row=0, col=1)
        Field(props, "水深+干舷 Z", self.var_depth, unit="m", row=1, col=0)
        Field(props, "未拉伸原长 ST", self.var_length, unit="m", row=1, col=1)
        Field(props, "预张力下限", self.var_pt_min, unit="ton", row=2, col=0)
        Field(props, "预张力上限", self.var_pt_max, unit="ton", row=2, col=1)
        Field(props, "预张力步长", self.var_pt_step, unit="ton", row=2, col=2)

        # 导缆孔表格
        ttk.Label(self.moor_body, text="导缆孔布置",
                  style="CardH2.TLabel").pack(anchor="w", pady=(12, 4))
        cols = ("name", "x", "y", "z", "angle", "enabled")
        heads = {"name": "编号", "x": "X (m)", "y": "Y (m)",
                 "z": "Z (m)", "angle": "水平角 (°)", "enabled": "启用"}
        widths = {"name": 60, "x": 90, "y": 90, "z": 90,
                  "angle": 100, "enabled": 60}
        tree = ttk.Treeview(self.moor_body, columns=cols, show="headings",
                            height=6)
        for c in cols:
            tree.heading(c, text=heads[c])
            tree.column(c, width=widths[c], anchor="center")
        for f in m.fairleads:
            tree.insert("", "end", values=(
                f.name, f.x, f.y, f.z, f.angle, "✓" if f.enabled else ""))
        tree.pack(fill="x")
        self.fairlead_tree = tree

        ttk.Label(self.moor_body,
                  text="注：A2 / B2 在计算中张力被强制置零，取消勾选即不参与。",
                  style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))

        ttk.Button(self.moor_body, text="计算悬链线曲线（占位）",
                   style="Ghost.TButton",
                   command=lambda: messagebox.showinfo(
                       "占位", "此处将绘制 x_jie–T_H 曲线与初始预张力标注。")
                   ).pack(anchor="w", pady=(10, 0))

    def _toggle_mooring(self) -> None:
        if self.moor_open.get():
            self.moor_body.pack(fill="x")
        else:
            self.moor_body.pack_forget()

    # ===================================================================== #
    #  工程读写
    # ===================================================================== #
    def collect(self) -> Project:
        """把界面上的值写回 Project 对象。"""
        p = self.project
        try:
            p.hydro.folder = self.var_hydro_dir.get()
            p.hydro.prefix = self.var_prefix.get().strip() or "WAMIT_5S"
            p.hydro.hbot = float(self.var_hbot.get())
            p.hydro.rho = float(self.var_rho.get())
            p.hydro.imode = [v.get() for v in self.dof_vars]

            p.wave.mode = self.var_wave_mode.get()
            p.wave.regular_h = float(self.var_reg_h.get())
            p.wave.regular_t = float(self.var_reg_t.get())
            p.wave.ramp = bool(self.var_ramp.get())
            p.wave.hs = float(self.var_hs.get())
            p.wave.tp = float(self.var_tp.get())
            p.wave.gamma = float(self.var_gamma.get())
            p.wave.duration = float(self.var_duration.get())
            p.wave.seed = int(self.var_seed.get())
            p.wave.wave_file = self.var_wave_file.get()
            p.wave.dt = float(self.var_dt.get())
            p.wave.numhum = int(self.var_numhum.get())

            m = p.mooring
            m.wet_weight = float(self.var_w.get())
            m.ea = float(self.var_ea.get())
            m.depth = float(self.var_depth.get())
            m.length = float(self.var_length.get())
            m.pretension_min = float(self.var_pt_min.get())
            m.pretension_max = float(self.var_pt_max.get())
            m.pretension_step = float(self.var_pt_step.get())
        except ValueError as exc:
            raise ValueError(f"参数格式错误：{exc}") from exc
        return p

    def _on_save(self) -> None:
        try:
            proj = self.collect()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return
        path = filedialog.asksaveasfilename(
            title="保存工程", defaultextension=".json",
            filetypes=[("工程文件", "*.json")])
        if path:
            proj.save(Path(path))
            self.app.log(f"工程已保存：{path}", "ok")

    def _on_load(self) -> None:
        path = filedialog.askopenfilename(
            title="加载工程", filetypes=[("工程文件", "*.json")])
        if not path:
            return
        try:
            proj = Project.load(Path(path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("加载失败", str(exc))
            return
        self.app.project = proj
        self.app.log(f"工程已加载：{path}", "ok")
        self.app.show_page(0)   # 重建页面以刷新控件


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
