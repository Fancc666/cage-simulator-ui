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
    WINDOW_MIN_W = 1120
    WINDOW_MIN_H = 740
    WINDOW_DEFAULT_W = 1280
    WINDOW_DEFAULT_H = 840

    SIDEBAR_W = 220
    PAD = 14
    PAD_S = 8
    PAD_L = 20
    RADIUS = 8


# --------------------------------------------------------------------------- #
#  字号（统一在这里调，全部 UI 跟着变）
# --------------------------------------------------------------------------- #
class FontSize:
    BASE = 11        # 正文 / 输入框 / 按钮
    SMALL = 10       # 提示文字
    CARD_TITLE = 13  # 卡片标题
    H1 = 20          # 页面大标题
    H2 = 15          # 区块标题
    NAV = 12         # 侧边导航
    LOG = 10         # 日志


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
    root.option_add("*Font", Fonts.get(FontSize.BASE))
    root.option_add("*TCombobox*Listbox.font", Fonts.get(FontSize.BASE))

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ---- 基础 ----
    # 注意：clam 主题会给每个控件画边框，这里统一压掉，只在需要的地方保留
    style.configure(".", font=Fonts.get(FontSize.BASE), background=Color.BG,
                    foreground=Color.TEXT, borderwidth=0)
    style.configure("TFrame", background=Color.BG, borderwidth=0)
    style.configure("Card.TFrame", background=Color.CARD, borderwidth=0,
                    relief="flat")
    style.configure("TLabel", background=Color.BG, foreground=Color.TEXT,
                    borderwidth=0)
    style.configure("Card.TLabel", background=Color.CARD, borderwidth=0)
    style.configure("Muted.TLabel", background=Color.BG,
                    foreground=Color.TEXT_MUTED, borderwidth=0)
    style.configure("CardMuted.TLabel", background=Color.CARD,
                    foreground=Color.TEXT_MUTED, borderwidth=0)
    style.configure("H1.TLabel", font=Fonts.get(FontSize.H1, "bold"))
    style.configure("H2.TLabel", font=Fonts.get(FontSize.H2, "bold"))
    style.configure("CardH2.TLabel", font=Fonts.get(FontSize.CARD_TITLE, "bold"),
                    background=Color.CARD)
    style.configure("Hint.TLabel", font=Fonts.get(FontSize.SMALL),
                    foreground=Color.TEXT_MUTED)

    # ---- 按钮 ----
    style.configure("TButton", padding=(14, 7), font=Fonts.get(FontSize.BASE),
                    borderwidth=0, relief="flat", background="#e8ecf1")
    style.map("TButton", background=[("active", "#dbe1e8")])
    style.configure("Primary.TButton", padding=(16, 8),
                    font=Fonts.get(FontSize.BASE, "bold"),
                    background=Color.PRIMARY, foreground=Color.TEXT_INVERSE,
                    borderwidth=0, relief="flat")
    style.map("Primary.TButton",
              background=[("active", Color.PRIMARY_HOVER),
                          ("disabled", "#93b4f5")])
    style.configure("Danger.TButton", padding=(16, 8),
                    font=Fonts.get(FontSize.BASE, "bold"),
                    background=Color.DANGER, foreground=Color.TEXT_INVERSE,
                    borderwidth=0, relief="flat")
    style.map("Danger.TButton",
              background=[("active", "#b91c1c"), ("disabled", "#f0a0a0")])
    style.configure("Ghost.TButton", padding=(12, 6), borderwidth=0,
                    relief="flat", background="#e8ecf1")

    # ---- 输入控件 ----
    style.configure("TEntry", padding=5, fieldbackground="#ffffff",
                    borderwidth=1, relief="solid", bordercolor=Color.BORDER)
    style.configure("TCombobox", padding=5, fieldbackground="#ffffff",
                    borderwidth=1, relief="solid", bordercolor=Color.BORDER)
    style.configure("TCheckbutton", background=Color.BG, borderwidth=0)
    style.configure("Card.TCheckbutton", background=Color.CARD, borderwidth=0)
    style.configure("TRadiobutton", background=Color.BG, borderwidth=0)
    style.configure("Card.TRadiobutton", background=Color.CARD, borderwidth=0)
    style.configure("TLabelframe", background=Color.BG, borderwidth=0)
    style.configure("TLabelframe.Label", background=Color.BG,
                    font=Fonts.get(FontSize.BASE, "bold"),
                    foreground=Color.TEXT)

    # ---- 进度条 ----
    style.configure("TProgressbar", thickness=18,
                    background=Color.PRIMARY, troughcolor="#e5e7eb",
                    borderwidth=0, relief="flat")

    # ---- 表格 ----
    style.configure("Treeview", rowheight=30, font=Fonts.get(FontSize.BASE),
                    background=Color.CARD, fieldbackground=Color.CARD,
                    borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", font=Fonts.get(FontSize.BASE, "bold"),
                    padding=(8, 8), borderwidth=0, relief="flat",
                    background="#eef1f5")
    style.map("Treeview.Heading", background=[("active", "#e2e7ee")])
    style.map("Treeview", background=[("selected", "#dbeafe")],
              foreground=[("selected", Color.TEXT)])

    # ---- 分隔线：只保留真正需要的，颜色调淡 ----
    style.configure("TSeparator", background="#e6e9ee")

    # ---- Notebook ----
    style.configure("TNotebook", background=Color.BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 8),
                    font=Fonts.get(FontSize.BASE))
    style.map("TNotebook.Tab",
              background=[("selected", Color.CARD)],
              foreground=[("selected", Color.PRIMARY)])
