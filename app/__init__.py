"""网箱时域运动模拟器 —— Tkinter 图形界面。

三个页面（输入 / 运行 / 结果）。计算由 ``app.core.engine`` 驱动
``CagePython`` 目录下的原始程序完成，``app.core.simulator`` 负责
把计算放到后台线程并回传进度事件。
"""

__version__ = "0.1.0"
APP_TITLE = "网箱时域运动模拟器"
APP_SUBTITLE = "Cage Time-Domain Motion Simulator"
