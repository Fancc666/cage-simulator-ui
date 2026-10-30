"""全局主题：颜色、字体、尺寸、ttk 样式。

所有页面统一从这里取样式，避免各页面各写一套颜色。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


# --------------------------------------------------------------------------- #
#  颜色
# --------------------------------------------------------------------------- #
class Color:
    BG = "#f4f6f8"            # 窗口底色
    SIDEBAR = "#1f2937"       # 侧边导航底色
    SIDEBAR_HOVER = "#374151"
    SIDEBAR_ACTIVE = "#2563eb"
    SIDEBAR_TEXT = "#d1d5db"
    SIDEBAR_TEXT_ACTIVE = "#ffffff"

    CARD = "#ffffff"          # 卡片 / 面板底色
    BORDER = "#d9dee5"        # 边框
    TEXT = "#1f2937"          # 主文字
    TEXT_MUTED = "#6b7280"    # 次要文字
    TEXT_INVERSE = "#ffffff"

    PRIMARY = "#2563eb"       # 主按钮
    PRIMARY_HOVER = "#1d4ed8"
    SUCCESS = "#16a34a"
    WARNING = "#d97706"
    DANGER = "#dc2626"

    OK = "#16a34a"
    MISSING = "#dc2626"
    UNKNOWN = "#9ca3af"

    LOG_BG = "#0f172a"
    LOG_FG = "#e2e8f0"


# --------------------------------------------------------------------------- #
#  尺寸
# --------------------------------------------------------------------------- #
class Size:
    WINDOW_MIN_W = 1080
    WINDOW_MIN_H = 720
    WINDOW_DEFAULT_W = 1240
    WINDOW_DEFAULT_H = 800

    SIDEBAR_W = 210
    PAD = 12
    PAD_S = 6
    PAD_L = 18
    RADIUS = 8


# --------------------------------------------------------------------------- #
#  字体
# --------------------------------------------------------------------------- #
_FONT_CANDIDATES = [
    "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
    "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC",
    "WenQuanYi Micro Hei", "SimHei", "Arial Unicode MS",
]


def pick_ui_font(root: tk.Misc) -> str:
    """选一个系统里可用的中文字体。"""
    available = set(tkfont.families(root))
    for name in _FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


class Fonts:
    """字体在 apply_theme 之后才可用。"""

    family: str = "TkDefaultFont"

    @classmethod
    def get(cls, size: int = 10, weight: str = "normal") -> tuple:
        return (cls.family, size, weight)


# --------------------------------------------------------------------------- #
#  主题应用
# --------------------------------------------------------------------------- #
def apply_theme(root: tk.Tk) -> None:
    Fonts.family = pick_ui_font(root)

    root.configure(bg=Color.BG)
    root.option_add("*Font", Fonts.get(10))
    root.option_add("*TCombobox*Listbox.font", Fonts.get(10))

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ---- 基础 ----
    style.configure(".", font=Fonts.get(10), background=Color.BG,
                    foreground=Color.TEXT)
    style.configure("TFrame", background=Color.BG)
    style.configure("Card.TFrame", background=Color.CARD,
                    relief="solid", borderwidth=1)
    style.configure("TLabel", background=Color.BG, foreground=Color.TEXT)
    style.configure("Card.TLabel", background=Color.CARD)
    style.configure("Muted.TLabel", background=Color.BG,
                    foreground=Color.TEXT_MUTED)
    style.configure("CardMuted.TLabel", background=Color.CARD,
                    foreground=Color.TEXT_MUTED)
    style.configure("H1.TLabel", font=Fonts.get(18, "bold"))
    style.configure("H2.TLabel", font=Fonts.get(13, "bold"))
    style.configure("CardH2.TLabel", font=Fonts.get(13, "bold"),
                    background=Color.CARD)
    style.configure("Hint.TLabel", font=Fonts.get(9),
                    foreground=Color.TEXT_MUTED)

    # ---- 按钮 ----
    style.configure("TButton", padding=(12, 6), font=Fonts.get(10))
    style.configure("Primary.TButton", padding=(14, 7),
                    font=Fonts.get(10, "bold"),
                    background=Color.PRIMARY, foreground=Color.TEXT_INVERSE,
                    borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", Color.PRIMARY_HOVER),
                          ("disabled", "#93b4f5")])
    style.configure("Danger.TButton", padding=(14, 7),
                    font=Fonts.get(10, "bold"),
                    background=Color.DANGER, foreground=Color.TEXT_INVERSE,
                    borderwidth=0)
    style.map("Danger.TButton",
              background=[("active", "#b91c1c"), ("disabled", "#f0a0a0")])
    style.configure("Ghost.TButton", padding=(10, 5), borderwidth=1)

    # ---- 输入控件 ----
    style.configure("TEntry", padding=4, fieldbackground="#ffffff")
    style.configure("TCombobox", padding=4, fieldbackground="#ffffff")
    style.configure("TCheckbutton", background=Color.BG)
    style.configure("Card.TCheckbutton", background=Color.CARD)
    style.configure("TRadiobutton", background=Color.BG)
    style.configure("Card.TRadiobutton", background=Color.CARD)
    style.configure("TLabelframe", background=Color.BG,
                    bordercolor=Color.BORDER)
    style.configure("TLabelframe.Label", background=Color.BG,
                    font=Fonts.get(10, "bold"), foreground=Color.TEXT)

    # ---- 进度条 ----
    style.configure("TProgressbar", thickness=16,
                    background=Color.PRIMARY, troughcolor="#e5e7eb",
                    borderwidth=0)

    # ---- 表格 ----
    style.configure("Treeview", rowheight=26, font=Fonts.get(10),
                    background=Color.CARD, fieldbackground=Color.CARD,
                    borderwidth=1)
    style.configure("Treeview.Heading", font=Fonts.get(10, "bold"),
                    padding=(6, 6))
    style.map("Treeview", background=[("selected", "#dbeafe")],
              foreground=[("selected", Color.TEXT)])

    # ---- 分隔线 ----
    style.configure("TSeparator", background=Color.BORDER)

    # ---- Notebook ----
    style.configure("TNotebook", background=Color.BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 7), font=Fonts.get(10))
    style.map("TNotebook.Tab",
              background=[("selected", Color.CARD)],
              foreground=[("selected", Color.PRIMARY)])
