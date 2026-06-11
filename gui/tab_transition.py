"""
gui/tab_transition.py  ——  转场控制标签页（PyQt5 版）
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QSlider,
)
from PyQt5.QtCore import Qt

from .utils import run_in_thread, FONT_BOLD

if TYPE_CHECKING:
    from .app import OBSGui


class TransitionTab(QWidget):
    """转场名称 / 时长 / T-Bar / Studio 模式切换。"""

    def __init__(self, parent, app: "OBSGui"):
        super().__init__(parent)
        self.app = app
        self._studio_on = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel("转场控制"))

        # 转场选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("转场效果:"))
        self._trans_cb = QComboBox()
        self._trans_cb.setFixedWidth(200)
        row1.addWidget(self._trans_cb)
        btn_refresh = QPushButton("🔄")
        btn_refresh.setProperty("outline", True)
        btn_refresh.clicked.connect(self._load_transitions)
        row1.addWidget(btn_refresh)
        row1.addStretch()
        layout.addLayout(row1)

        # 转场时长
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("时长 (ms):"))
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(0, 10000)
        self._duration_spin.setSingleStep(100)
        self._duration_spin.setValue(300)
        row2.addWidget(self._duration_spin)
        row2.addStretch()
        layout.addLayout(row2)

        # 应用按钮
        btn_apply = QPushButton("应用转场设置")
        btn_apply.clicked.connect(self._apply_transition)
        layout.addWidget(btn_apply)

        layout.addSpacing(8)

        # T-Bar
        layout.addWidget(QLabel("T-Bar 手动过渡"))
        tbar_row = QHBoxLayout()
        tbar_row.addWidget(QLabel("0%"))
        self._tbar = QSlider(Qt.Horizontal)
        self._tbar.setRange(0, 100)
        self._tbar.setValue(0)
        self._tbar.setFixedWidth(260)
        self._tbar.valueChanged.connect(self._on_tbar)
        tbar_row.addWidget(self._tbar)
        tbar_row.addWidget(QLabel("100%"))
        tbar_row.addStretch()
        layout.addLayout(tbar_row)

        self._tbar_label = QLabel("当前位置: 0.00")
        self._tbar_label.setStyleSheet("color: #375a7f;")
        layout.addWidget(self._tbar_label)

        layout.addSpacing(8)

        # Studio Mode
        layout.addWidget(QLabel("Studio 模式"))
        studio_row = QHBoxLayout()
        self._studio_btn = QPushButton("开启 Studio 模式")
        self._studio_btn.setProperty("outline", True)
        self._studio_btn.setFixedWidth(180)
        self._studio_btn.clicked.connect(self._toggle_studio)
        studio_row.addWidget(self._studio_btn)
        studio_row.addStretch()
        layout.addLayout(studio_row)

        layout.addStretch()

    # ── 刷新转场列表 ──────────────────────────────────────────

    def _load_transitions(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(ctrl.get_transition_list, self._on_transitions)

    def _on_transitions(self, data) -> None:
        if isinstance(data, dict):
            transitions = data.get("transitions", [])
            current = data.get("currentTransitionName", "")
        elif hasattr(data, "transitions"):
            transitions = data.transitions
            current = getattr(data, "current_scene_transition_name", "")
        else:
            transitions = []
            current = ""

        names = []
        for t in transitions:
            if isinstance(t, dict):
                names.append(t.get("transitionName", ""))
            elif hasattr(t, "transition_name"):
                names.append(t.transition_name)

        self._trans_cb.clear()
        self._trans_cb.addItems(names)
        idx = names.index(current) if current in names else 0
        if names:
            self._trans_cb.setCurrentIndex(idx)

    # ── 应用转场 ──────────────────────────────────────────────

    def _apply_transition(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        name = self._trans_cb.currentText()
        duration = self._duration_spin.value()
        if name:
            self.app.log(f"转场设置: {name} / {duration}ms", "INFO")
            run_in_thread(
                lambda: (
                    ctrl.set_current_transition(name),
                    ctrl.set_transition_duration(duration),
                ),
            )

    # ── T-Bar ─────────────────────────────────────────────────

    def _on_tbar(self, val: int) -> None:
        v = val / 100.0
        self._tbar_label.setText(f"当前位置: {v:.2f}")
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(lambda: ctrl.set_tbar_position(v))

    # ── Studio 模式 ───────────────────────────────────────────

    def _toggle_studio(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self._studio_on = not self._studio_on
        run_in_thread(
            lambda: ctrl.req.set_studio_mode_enabled(
                studio_mode_enabled=self._studio_on
            ),
            lambda _: self._update_studio_btn(),
        )

    def _update_studio_btn(self) -> None:
        if self._studio_on:
            self._studio_btn.setText("关闭 Studio 模式")
            self._studio_btn.setProperty("warning", True)
            self.app.log("Studio 模式已开启", "INFO")
        else:
            self._studio_btn.setText("开启 Studio 模式")
            self._studio_btn.setProperty("outline", True)
            self.app.log("Studio 模式已关闭", "INFO")
        self._studio_btn.style().polish(self._studio_btn)

    def refresh(self) -> None:
        self._load_transitions()
