"""主窗口：侧边导航 + 步骤条 + 页面容器 + 底部状态栏。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import APP_SUBTITLE, APP_TITLE, __version__
from app.core.config import Project
from app.pages import InputPage, ResultPage, RunPage
from app.paths import LOGS_DIR, ensure_dir
from app.theme import Color, FontSize, Fonts, Size, apply_theme
from app.widgets import Stepper


PAGE_NAMES = ["输入", "运行", "结果"]


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  v{__version__}")
        self.geometry(f"{Size.WINDOW_DEFAULT_W}x{Size.WINDOW_DEFAULT_H}")
        self.minsize(Size.WINDOW_MIN_W, Size.WINDOW_MIN_H)

        apply_theme(self)

        self.project = Project()
        self._current_page = -1

        self._build_layout()
        self._build_pages()
        self.show_page(0)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ===================================================================== #
    #  布局
    # ===================================================================== #
    def _build_layout(self) -> None:
        # ---- 侧边导航 ----
        sidebar = tk.Frame(self, bg=Color.SIDEBAR, width=Size.SIDEBAR_W)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=Color.SIDEBAR)
        brand.pack(fill="x", pady=(26, 28), padx=20)
        tk.Label(brand, text="网箱时域", bg=Color.SIDEBAR,
                 fg=Color.SIDEBAR_TEXT_ACTIVE,
                 font=Fonts.get(17, "bold"), anchor="w").pack(fill="x")
        tk.Label(brand, text=APP_SUBTITLE, bg=Color.SIDEBAR,
                 fg=Color.SIDEBAR_TEXT, font=Fonts.get(FontSize.SMALL),
                 anchor="w").pack(fill="x", pady=(2, 0))

        self.nav_buttons: list[tk.Label] = []
        for i, name in enumerate(PAGE_NAMES):
            lbl = tk.Label(sidebar, text=f"  {i + 1}   {name}",
                           bg=Color.SIDEBAR, fg=Color.SIDEBAR_TEXT,
                           font=Fonts.get(FontSize.NAV), anchor="w",
                           padx=20, pady=13)
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda _e, idx=i: self.show_page(idx))
            lbl.bind("<Enter>", lambda _e, w=lbl: self._nav_hover(w, True))
            lbl.bind("<Leave>", lambda _e, w=lbl: self._nav_hover(w, False))
            self.nav_buttons.append(lbl)

        # 底部版本号
        tk.Label(sidebar, text=f"v{__version__}", bg=Color.SIDEBAR,
                 fg=Color.SIDEBAR_TEXT, font=Fonts.get(FontSize.SMALL),
                 anchor="w", padx=20, pady=16).pack(side="bottom", fill="x")

        # ---- 右侧主区域 ----
        main = ttk.Frame(self)
        main.pack(side="left", fill="both", expand=True)

        # 顶部步骤条
        top = ttk.Frame(main, padding=(20, 14, 20, 0))
        top.pack(fill="x")
        self.stepper = Stepper(top, PAGE_NAMES, on_click=self.show_page)
        self.stepper.pack(side="left")

        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(12, 0))

        # 页面容器
        self.page_container = ttk.Frame(main)
        self.page_container.pack(fill="both", expand=True)

        # 底部状态栏
        status = ttk.Frame(main, padding=(20, 5, 20, 7))
        status.pack(fill="x", side="bottom")
        ttk.Separator(main, orient="horizontal").pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status, textvariable=self.status_var,
                  style="Hint.TLabel").pack(side="left")

    def _nav_hover(self, widget: tk.Label, entering: bool) -> None:
        idx = self.nav_buttons.index(widget)
        if idx == self._current_page:
            return
        widget.configure(bg=Color.SIDEBAR_HOVER if entering else Color.SIDEBAR)

    # ===================================================================== #
    #  页面
    # ===================================================================== #
    def _build_pages(self) -> None:
        self.input_page = InputPage(self.page_container, self)
        self.run_page = RunPage(self.page_container, self)
        self.result_page = ResultPage(self.page_container, self)
        self.pages = [self.input_page, self.run_page, self.result_page]

    def show_page(self, idx: int) -> None:
        if idx == self._current_page:
            return
        for page in self.pages:
            page.pack_forget()
        self.pages[idx].pack(fill="both", expand=True)
        self._current_page = idx

        # 导航高亮
        for i, lbl in enumerate(self.nav_buttons):
            if i == idx:
                lbl.configure(bg=Color.SIDEBAR_ACTIVE,
                              fg=Color.SIDEBAR_TEXT_ACTIVE)
            else:
                lbl.configure(bg=Color.SIDEBAR, fg=Color.SIDEBAR_TEXT)
        self.stepper.set_current(idx)

        # 页面钩子
        page = self.pages[idx]
        if hasattr(page, "on_show"):
            page.on_show()

    # ===================================================================== #
    #  公共
    # ===================================================================== #
    def log(self, msg: str, level: str = "info") -> None:
        self.status_var.set(msg)
        try:
            ensure_dir(LOGS_DIR)
            with open(LOGS_DIR / "ui.log", "a", encoding="utf-8") as f:
                f.write(f"[{level}] {msg}\n")
        except OSError:
            pass

    def _on_close(self) -> None:
        runner = getattr(self.run_page, "runner", None)
        if runner is not None and runner.is_running:
            if not messagebox.askyesno("确认退出", "仿真仍在运行，确定退出吗？"):
                return
            runner.stop()
        self.destroy()
