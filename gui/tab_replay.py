"""
gui/tab_replay.py  ——  回放缓冲 + 截图标签页（PyQt5 版）
"""
from __future__ import annotations

import io
import base64
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSlider, QGroupBox,
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

from .utils import run_in_thread, FONT_BOLD, FONT_LABEL

if TYPE_CHECKING:
    from .app import OBSGui


THUMB_W, THUMB_H = 256, 144


class ReplayTab(QWidget):
    """回放缓冲控制 + 截图功能。"""

    def __init__(self, parent, app: "OBSGui"):
        super().__init__(parent)
        self.app = app
        self._replay_on = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── 回放缓冲 ──
        buf_group = QGroupBox(" 📼 回放缓冲 ")
        buf_layout = QVBoxLayout(buf_group)

        b1 = QHBoxLayout()
        self._buf_btn = QPushButton("▶ 启动缓冲")
        self._buf_btn.setProperty("success", True)
        self._buf_btn.setFixedWidth(130)
        self._buf_btn.clicked.connect(self._toggle_replay)
        b1.addWidget(self._buf_btn)

        btn_save = QPushButton("💾 保存回放")
        btn_save.setProperty("outline", True)
        btn_save.setFixedWidth(130)
        btn_save.clicked.connect(self._save_replay)
        b1.addWidget(btn_save)
        b1.addStretch()
        buf_layout.addLayout(b1)

        b2 = QHBoxLayout()
        b2.addWidget(QLabel("最近保存:"))
        self._saved_path_label = QLabel("（未保存）")
        self._saved_path_label.setStyleSheet("color: #375a7f;")
        b2.addWidget(self._saved_path_label)
        b2.addStretch()
        buf_layout.addLayout(b2)

        layout.addWidget(buf_group)

        # ── 截图 ──
        shot_group = QGroupBox(" 📷 截图 ")
        shot_layout = QVBoxLayout(shot_group)

        s1 = QHBoxLayout()
        s1.addWidget(QLabel("输入源:"))
        self._shot_src_cb = QComboBox()
        self._shot_src_cb.setFixedWidth(200)
        s1.addWidget(self._shot_src_cb)
        btn_refresh = QPushButton("🔄")
        btn_refresh.setProperty("outline", True)
        btn_refresh.clicked.connect(self._load_sources)
        s1.addWidget(btn_refresh)
        s1.addStretch()
        shot_layout.addLayout(s1)

        s2 = QHBoxLayout()
        s2.addWidget(QLabel("格式:"))
        self._fmt_cb = QComboBox()
        self._fmt_cb.addItems(["jpg", "png", "webp", "bmp"])
        self._fmt_cb.setFixedWidth(70)
        s2.addWidget(self._fmt_cb)

        s2.addWidget(QLabel("质量:"))
        self._quality_slider = QSlider(Qt.Horizontal)
        self._quality_slider.setRange(1, 100)
        self._quality_slider.setValue(85)
        self._quality_slider.setFixedWidth(120)
        s2.addWidget(self._quality_slider)

        self._quality_lbl = QLabel("85")
        self._quality_lbl.setFixedWidth(30)
        self._quality_slider.valueChanged.connect(
            lambda v: self._quality_lbl.setText(str(v))
        )
        s2.addWidget(self._quality_lbl)
        s2.addStretch()
        shot_layout.addLayout(s2)

        btn_shot = QPushButton("📸 立即截图")
        btn_shot.clicked.connect(self._take_screenshot)
        shot_layout.addWidget(btn_shot)

        # 缩略图显示
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(THUMB_W, THUMB_H)
        self._thumb_label.setAlignment(Qt.AlignCenter)
        self._thumb_label.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #444444;"
        )
        self._thumb_label.setText("截图预览")
        shot_layout.addWidget(self._thumb_label, alignment=Qt.AlignCenter)

        layout.addWidget(shot_group)
        layout.addStretch()

    # ── 回放缓冲控制 ──────────────────────────────────────────

    def _toggle_replay(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._replay_on:
            run_in_thread(ctrl.start_replay_buffer, lambda _: self._set_replay(True))
        else:
            run_in_thread(ctrl.stop_replay_buffer, lambda _: self._set_replay(False))

    def _set_replay(self, on: bool) -> None:
        self._replay_on = on
        self._buf_btn.setText("⏹ 停止缓冲" if on else "▶ 启动缓冲")
        if on:
            self._buf_btn.setProperty("danger", True)
        else:
            self._buf_btn.setProperty("success", True)
        self._buf_btn.style().polish(self._buf_btn)

    def _save_replay(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            ctrl.save_replay_buffer,
            self._on_replay_saved,
        )

    def _on_replay_saved(self, res) -> None:
        if isinstance(res, dict):
            path = res.get("savedReplayPath", "")
        elif hasattr(res, "saved_replay_path"):
            path = res.saved_replay_path
        else:
            path = str(res)
        self._saved_path_label.setText(path or "（已保存）")

    # ── 截图 ─────────────────────────────────────────────────

    def _load_sources(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(ctrl.get_input_list, self._on_sources)

    def _on_sources(self, inputs: list) -> None:
        names = []
        for inp in inputs:
            n = inp if isinstance(inp, str) else inp.get("name", "")
            if n:
                names.append(n)
        self._shot_src_cb.clear()
        self._shot_src_cb.addItems(names)
        if names:
            self._shot_src_cb.setCurrentIndex(0)

    def _take_screenshot(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        src = self._shot_src_cb.currentText()
        fmt = self._fmt_cb.currentText()
        quality = self._quality_slider.value()
        if not src:
            return
        run_in_thread(
            lambda: ctrl.get_source_screenshot(
                source_name=src, img_format=fmt,
                width=THUMB_W * 2, height=THUMB_H * 2,
                quality=quality,
            ),
            self._show_thumb,
        )

    def _show_thumb(self, b64: str) -> None:
        try:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            raw = base64.b64decode(b64)
            img = QImage()
            img.loadFromData(raw)
            if not img.isNull():
                scaled = img.scaled(
                    THUMB_W, THUMB_H,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self._thumb_label.setPixmap(QPixmap.fromImage(scaled))
                self._thumb_label.setText("")
        except Exception:
            pass

    def refresh(self) -> None:
        self._load_sources()
