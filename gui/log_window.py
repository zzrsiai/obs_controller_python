"""
gui/log_window.py  ——  左下角日志输出窗口
支持分级彩色日志、时间戳、自动滚动、线程安全写入
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import FONT_MONO, CLR_GREEN, CLR_RED, CLR_YELLOW, CLR_SUBTEXT

if TYPE_CHECKING:
    from .app import OBSGui


class LogWindow:
    """左下角日志输出面板。

    使用方式:
        app.log("场景已切换", "INFO")
        app.log("连接失败: timeout", "ERROR")
        app.log("录制已开始", "SUCCESS")
    """

    MAX_LINES = 500  # 超过后裁剪前一半

    # 日志等级 → (颜色, 前缀图标)
    LEVEL_STYLES = {
        "INFO":    ("#cccccc", "[INFO]"),
        "SUCCESS": (CLR_GREEN, "[SUCCESS]"),
        "WARNING": (CLR_YELLOW, "[WARNING]"),
        "ERROR":   (CLR_RED,   "[ERROR]"),
        "DEBUG":   (CLR_SUBTEXT, "[DEBUG]"),
    }

    def __init__(self, parent: tk.Widget, app: "OBSGui"):
        self.app = app
        self.root = app.root

        # 外框
        self.frame = ttk_bs.Labelframe(parent, text=" 📜 日志输出 ", padding=(2, 2))
        # 不在 __init__ 中 pack，由调用方决定布局

        # 容器
        container = ttk_bs.Frame(self.frame)
        container.pack(fill="both", expand=True)

        # 文本区 + 滚动条
        self._text = tk.Text(
            container,
            wrap="word",
            font=FONT_MONO,
            bg="#1a1a1a",
            fg="#cccccc",
            insertbackground="#cccccc",
            relief="flat",
            borderwidth=0,
            padx=6, pady=4,
            state="disabled",
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

        # 配置颜色标签
        for level, (color, _) in self.LEVEL_STYLES.items():
            self._text.tag_configure(level, foreground=color)
        self._text.tag_configure("timestamp", foreground="#888888")

        self._line_count = 0

    # ── 公开方法 ────────────────────────────────────────────

    def log(self, message: str, level: str = "INFO") -> None:
        """线程安全地写入一条日志。可从任意线程调用。"""
        self.root.after(0, lambda: self._write(message, level))

    def clear(self) -> None:
        """清空所有日志。"""
        self.root.after(0, self._clear)

    # ── 内部实现 ────────────────────────────────────────────

    def _write(self, message: str, level: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        style = self.LEVEL_STYLES.get(level.upper(), self.LEVEL_STYLES["INFO"])
        color_tag = level.upper() if level.upper() in self.LEVEL_STYLES else "INFO"
        icon = style[1]

        self._text.configure(state="normal")

        # 时间戳
        self._text.insert("end", f"[{now}] ", "timestamp")
        # 等级图标 + 内容
        self._text.insert("end", f"{icon} {message}\n", color_tag)

        self._text.configure(state="disabled")
        self._text.see("end")

        self._line_count += 1
        self._trim_if_needed()

    def _clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        self._line_count = 0

    def _trim_if_needed(self) -> None:
        """日志行数超过上限时，删除前半部分。"""
        if self._line_count <= self.MAX_LINES:
            return
        # 保留后一半
        keep = self.MAX_LINES // 2
        self._text.configure(state="normal")
        # 数 keep 行从末尾往前
        last = int(self._text.index("end-1c").split(".")[0])
        if last > keep:
            self._text.delete("1.0", f"{last - keep + 1}.0")
        self._text.configure(state="disabled")
        self._line_count = keep
