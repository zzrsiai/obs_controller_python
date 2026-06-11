"""
gui/utils.py  ——  PyQt5 公共常量 & 线程安全工具
"""
from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from typing import Callable, Any, Optional


# ── 颜色常量（暗色主题） ──────────────────────────────────────────
CLR_BG        = "#222222"
CLR_PANEL     = "#2b2b2b"
CLR_ACCENT    = "#375a7f"
CLR_GREEN     = "#00bc8c"
CLR_RED       = "#e74c3c"
CLR_YELLOW    = "#f39c12"
CLR_TEXT      = "#ffffff"
CLR_SUBTEXT   = "#aaaaaa"

# ── 字体 ────────────────────────────────────────────────────────
FONT_LABEL    = ("Segoe UI", 9)
FONT_BOLD     = ("Segoe UI", 9, "bold")
FONT_TITLE    = ("Segoe UI", 10, "bold")
FONT_BIG      = ("Segoe UI", 18, "bold")
FONT_MONO     = ("Consolas", 9)

PREVIEW_W = 480
PREVIEW_H = 270


# ── 全局线程池 ────────────────────────────────────────────────────
_thread_pool = QThreadPool.globalInstance()


class _WorkerSignals(QObject):
    """Worker 的信号集。"""
    finished = pyqtSignal(object)   # 正常结果
    error    = pyqtSignal(Exception)  # 异常


class _Worker(QRunnable):
    """在 QThreadPool 中执行 fn，通过信号回传结果。"""

    def __init__(self, fn: Callable[[], Any], signals: _WorkerSignals):
        super().__init__()
        self.fn = fn
        self.signals = signals

    def run(self):
        try:
            result = self.fn()
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.error.emit(exc)


def run_in_thread(
    fn: Callable[[], Any],
    ok_cb: Optional[Callable[[Any], None]] = None,
    err_cb: Optional[Callable[[Exception], None]] = None,
) -> None:
    """在 QThreadPool 线程中执行 fn，结果通过信号回调到主线程。"""
    signals = _WorkerSignals()
    if ok_cb:
        signals.finished.connect(ok_cb)
    if err_cb:
        signals.error.connect(err_cb)
    worker = _Worker(fn, signals)
    _thread_pool.start(worker)


def format_timecode(ms: int) -> str:
    """毫秒 → HH:MM:SS 字符串。"""
    if ms < 0:
        return "--:--:--"
    s  = ms // 1000
    h  = s  // 3600
    m  = (s % 3600) // 60
    s  = s  % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── 通用暗色 QSS 样式表 ──────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #222222;
    color: #ffffff;
    font-family: "Segoe UI";
    font-size: 9pt;
}
QGroupBox {
    border: 1px solid #444444;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #375a7f;
    border: 1px solid #4a6fa5;
    border-radius: 3px;
    padding: 4px 12px;
    color: #ffffff;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #4a6fa5;
}
QPushButton:pressed {
    background-color: #2c4a6e;
}
QPushButton:disabled {
    background-color: #333333;
    color: #666666;
    border-color: #444444;
}
QPushButton[danger="true"] {
    background-color: #e74c3c;
    border-color: #c0392b;
}
QPushButton[danger="true"]:hover {
    background-color: #c0392b;
}
QPushButton[success="true"] {
    background-color: #00bc8c;
    border-color: #00a67d;
}
QPushButton[success="true"]:hover {
    background-color: #00a67d;
}
QPushButton[warning="true"] {
    background-color: #f39c12;
    border-color: #d68910;
    color: #222222;
}
QPushButton[warning="true"]:hover {
    background-color: #d68910;
}
QPushButton[outline="true"] {
    background-color: transparent;
    border: 1px solid #375a7f;
    color: #375a7f;
}
QPushButton[outline="true"]:hover {
    background-color: #2c3e50;
}
QLineEdit {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 3px;
    padding: 3px 6px;
    color: #ffffff;
}
QLineEdit:focus {
    border-color: #375a7f;
}
QComboBox {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 3px;
    padding: 3px 6px;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    color: #ffffff;
    selection-background-color: #375a7f;
}
QListWidget {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 3px;
    color: #ffffff;
    outline: none;
}
QListWidget::item {
    padding: 4px;
}
QListWidget::item:selected {
    background-color: #375a7f;
}
QTableWidget {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    gridline-color: #444444;
    color: #ffffff;
}
QTableWidget::item {
    padding: 2px 4px;
}
QTableWidget::item:selected {
    background-color: #375a7f;
}
QHeaderView::section {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #444444;
    padding: 4px;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #444444;
    background-color: #222222;
}
QTabBar::tab {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    padding: 6px 14px;
    color: #cccccc;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #375a7f;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #333333;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #444444;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #375a7f;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #00bc8c;
    border-radius: 3px;
}
QSpinBox {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 3px;
    padding: 2px 4px;
    color: #ffffff;
}
QTextEdit {
    background-color: #1a1a1a;
    color: #cccccc;
    border: 1px solid #444444;
    font-family: Consolas;
    font-size: 9pt;
}
QSplitter::handle {
    background-color: #444444;
}
QScrollBar:vertical {
    background-color: #2b2b2b;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QStatusBar {
    background-color: #1a1a1a;
    color: #cccccc;
    border-top: 1px solid #444444;
}
QStatusBar::item {
    border-right: 1px solid #444444;
    padding: 0 6px;
}
QLabel[status="connected"] {
    color: #00bc8c;
}
QLabel[status="disconnected"] {
    color: #e74c3c;
}
"""
