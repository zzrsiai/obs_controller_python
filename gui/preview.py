"""
gui/preview.py  ——  双画面预览区（PROGRAM / PREVIEW）+ 转场快捷按钮（PyQt5 版）
"""
from __future__ import annotations

import io
import base64
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QSlider, QWidget, QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

from .utils import PREVIEW_W, PREVIEW_H, CLR_GREEN, CLR_RED, run_in_thread

if TYPE_CHECKING:
    from .app import OBSGui


class PreviewPanel(QGroupBox):
    """左侧双画面预览区（PROGRAM + PREVIEW）及转场快捷按钮。"""

    def __init__(self, parent, app: "OBSGui"):
        super().__init__(" 📺 预览监视器 ", parent)
        self.app = app
        self._preview_locked_scene: str | None = None

        self._init_ui()

        # 定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frames)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 上方：两个预览画面并排
        canvas_row = QHBoxLayout()

        # PROGRAM
        prog_col = QVBoxLayout()
        prog_label = QLabel("🔴  PROGRAM")
        prog_label.setAlignment(Qt.AlignCenter)
        prog_label.setStyleSheet("font-weight: bold;")
        prog_col.addWidget(prog_label)

        self.program_label = QLabel()
        self.program_label.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.program_label.setAlignment(Qt.AlignCenter)
        self.program_label.setStyleSheet(
            f"background-color: #1a1a1a; border: 2px solid {CLR_RED};"
        )
        self.program_label.setText("PROGRAM\n（未连接）")
        prog_col.addWidget(self.program_label)
        canvas_row.addLayout(prog_col)

        # PREVIEW
        prev_col = QVBoxLayout()
        prev_label = QLabel("🟢  PREVIEW")
        prev_label.setAlignment(Qt.AlignCenter)
        prev_label.setStyleSheet("font-weight: bold;")
        prev_col.addWidget(prev_label)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            f"background-color: #1a1a1a; border: 2px solid {CLR_GREEN};"
        )
        self.preview_label.setText("PREVIEW\n（未连接）")
        prev_col.addWidget(self.preview_label)
        canvas_row.addLayout(prev_col)

        layout.addLayout(canvas_row)

        # 下方：转场控制行
        ctrl = QHBoxLayout()

        btn_cut = QPushButton("CUT")
        btn_cut.setProperty("danger", True)
        btn_cut.setFixedWidth(70)
        btn_cut.clicked.connect(self.app.do_cut)
        ctrl.addWidget(btn_cut)

        btn_fade = QPushButton("FADE")
        btn_fade.setFixedWidth(70)
        btn_fade.clicked.connect(self.app.do_fade)
        ctrl.addWidget(btn_fade)

        btn_black = QPushButton("🌑 黑场")
        btn_black.setProperty("outline", True)
        btn_black.setFixedWidth(80)
        btn_black.clicked.connect(self.app.do_fade_to_black)
        ctrl.addWidget(btn_black)

        ctrl.addSpacing(10)

        ctrl.addWidget(QLabel("T-Bar:"))
        self.tbar_slider = QSlider(Qt.Horizontal)
        self.tbar_slider.setRange(0, 100)
        self.tbar_slider.setValue(0)
        self.tbar_slider.setFixedWidth(180)
        self.tbar_slider.valueChanged.connect(self._on_tbar)
        ctrl.addWidget(self.tbar_slider)

        ctrl.addStretch()

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.setProperty("outline", True)
        btn_refresh.clicked.connect(self.app.refresh_all)
        ctrl.addWidget(btn_refresh)

        layout.addLayout(ctrl)

    # ── 预览更新循环 ─────────────────────────────────────────

    def start_loop(self) -> None:
        """连接成功后调用，启动 500ms 刷新循环。"""
        self.program_label.setText("连接中…")
        self.preview_label.setText("连接中…")
        self._timer.start(500)

    def stop_loop(self) -> None:
        """断开连接时停止循环。"""
        self._timer.stop()
        self._preview_locked_scene = None
        self.program_label.setText("PROGRAM\n（未连接）")
        self.program_label.setPixmap(QPixmap())
        self.preview_label.setText("PREVIEW\n（未连接）")
        self.preview_label.setPixmap(QPixmap())

    def preview_one_shot(self, scene_name: str) -> None:
        """在 PREVIEW 画面上显示指定场景的截图。"""
        ctrl = self.app.ctrl
        if ctrl is None:
            self.app.log("预览失败: 未连接到 OBS", "WARNING")
            return

        self._preview_locked_scene = scene_name
        self.app.log(f"正在预览场景: {scene_name}", "INFO")

        def fetch():
            return ctrl.get_source_screenshot(
                source_name=scene_name,
                img_format="jpg", width=PREVIEW_W, height=PREVIEW_H,
                quality=60,
            )

        run_in_thread(
            fetch,
            lambda b64: self._put_image(self.preview_label, b64),
        )

    def _update_frames(self) -> None:
        """每 500ms 获取一次截图并更新两块画面。"""
        ctrl = self.app.ctrl
        if ctrl is None:
            return

        override = self._preview_locked_scene

        # PROGRAM
        def fetch_program():
            cur_scene = ctrl.get_current_scene()
            return ("program", ctrl.get_source_screenshot(
                source_name=cur_scene,
                img_format="jpg", width=PREVIEW_W, height=PREVIEW_H,
                quality=60,
            ))

        def on_program(result):
            _, b64 = result
            self._put_image(self.program_label, b64)

        run_in_thread(fetch_program, on_program)

        # PREVIEW
        def fetch_preview():
            if override:
                prev_scene = override
            else:
                try:
                    prev_scene = ctrl.get_current_preview_scene() or ctrl.get_current_scene()
                except Exception:
                    prev_scene = ctrl.get_current_scene()
            return ("preview", ctrl.get_source_screenshot(
                source_name=prev_scene,
                img_format="jpg", width=PREVIEW_W, height=PREVIEW_H,
                quality=60,
            ))

        def on_preview(result):
            _, b64 = result
            self._put_image(self.preview_label, b64)

        run_in_thread(fetch_preview, on_preview)

    def _put_image(self, label: QLabel, b64: str) -> None:
        """解码 base64 JPEG 并显示到 QLabel。"""
        try:
            if isinstance(b64, str) and "," in b64:
                b64 = b64.split(",", 1)[1]
            raw = base64.b64decode(b64)
            img = QImage()
            img.loadFromData(raw)
            if not img.isNull():
                scaled = img.scaled(
                    PREVIEW_W, PREVIEW_H,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                label.setPixmap(QPixmap.fromImage(scaled))
                label.setText("")
        except Exception:
            label.setText("截图加载失败")

    # ── T-Bar 回调 ────────────────────────────────────────────

    def _on_tbar(self, val: int) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        v = val / 100.0
        run_in_thread(lambda: ctrl.set_tbar_position(v))
