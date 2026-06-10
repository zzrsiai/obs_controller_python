"""
gui/utils.py  ——  线程安全工具 & 公共常量
"""
from __future__ import annotations
import threading
import tkinter as tk
from typing import Callable, Any, Optional


# ── 颜色/字体常量（与 darkly 主题匹配） ──────────────────────────
CLR_BG        = "#222222"
CLR_PANEL     = "#2b2b2b"
CLR_ACCENT    = "#375a7f"
CLR_GREEN     = "#00bc8c"
CLR_RED       = "#e74c3c"
CLR_YELLOW    = "#f39c12"
CLR_TEXT      = "#ffffff"
CLR_SUBTEXT   = "#aaaaaa"

FONT_LABEL    = ("Segoe UI", 9)
FONT_BOLD     = ("Segoe UI", 9, "bold")
FONT_TITLE    = ("Segoe UI", 10, "bold")
FONT_BIG      = ("Segoe UI", 18, "bold")
FONT_MONO     = ("Consolas", 9)

PREVIEW_W = 480
PREVIEW_H = 270


# ── 线程安全执行 ────────────────────────────────────────────────

def run_in_thread(
    root: tk.Tk,
    fn: Callable[[], Any],
    ok_cb: Optional[Callable[[Any], None]] = None,
    err_cb: Optional[Callable[[Exception], None]] = None,
) -> None:
    """在子线程中执行 fn，结果通过 root.after(0, …) 回调主线程。"""
    import traceback as _tb
    def worker():
        try:
            result = fn()
            if ok_cb:
                root.after(0, lambda r=result: ok_cb(r))
        except Exception as exc:
            _tb.print_exc()
            if err_cb:
                root.after(0, lambda e=exc: err_cb(e))

    threading.Thread(target=worker, daemon=True).start()


def format_timecode(ms: int) -> str:
    """毫秒 → HH:MM:SS 字符串。"""
    if ms < 0:
        return "--:--:--"
    s  = ms // 1000
    h  = s  // 3600
    m  = (s % 3600) // 60
    s  = s  % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
