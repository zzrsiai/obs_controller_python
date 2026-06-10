"""
gui/tab_transition.py  ——  转场控制标签页
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import run_in_thread, FONT_BOLD

if TYPE_CHECKING:
    from .app import OBSGui


class TransitionTab:
    """转场名称 / 时长 / T-Bar / Studio 模式切换。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self.frame = ttk_bs.Frame(notebook, padding=12)
        notebook.add(self.frame, text="🎞 转场")
        self._build()

    def _build(self) -> None:
        ttk_bs.Label(self.frame, text="转场控制", font=FONT_BOLD).pack(
            anchor="w", pady=(0, 8)
        )

        # 转场选择
        row1 = ttk_bs.Frame(self.frame)
        row1.pack(fill="x", pady=4)
        ttk_bs.Label(row1, text="转场效果:", width=12).pack(side="left")
        self._trans_var = tk.StringVar()
        self._trans_cb = ttk_bs.Combobox(
            row1, textvariable=self._trans_var, width=24, state="readonly"
        )
        self._trans_cb.pack(side="left", padx=4)
        ttk_bs.Button(row1, text="🔄", bootstyle="secondary-outline",
                      command=self._load_transitions).pack(side="left", padx=4)

        # 转场时长
        row2 = ttk_bs.Frame(self.frame)
        row2.pack(fill="x", pady=4)
        ttk_bs.Label(row2, text="时长 (ms):", width=12).pack(side="left")
        self._duration_var = tk.IntVar(value=300)
        ttk_bs.Spinbox(
            row2, textvariable=self._duration_var,
            from_=0, to=10000, increment=100, width=8
        ).pack(side="left", padx=4)

        # 应用按钮
        ttk_bs.Button(
            self.frame, text="应用转场设置", bootstyle="primary",
            command=self._apply_transition
        ).pack(anchor="w", pady=8)

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=8)

        # T-Bar
        ttk_bs.Label(self.frame, text="T-Bar 手动过渡", font=FONT_BOLD).pack(anchor="w")
        tbar_row = ttk_bs.Frame(self.frame)
        tbar_row.pack(fill="x", pady=6)
        ttk_bs.Label(tbar_row, text="0%").pack(side="left")
        self._tbar_var = tk.DoubleVar(value=0.0)
        self._tbar = ttk_bs.Scale(
            tbar_row, from_=0.0, to=1.0, orient="horizontal",
            variable=self._tbar_var, length=260,
            command=self._on_tbar,
        )
        self._tbar.pack(side="left", padx=6)
        ttk_bs.Label(tbar_row, text="100%").pack(side="left")

        # 实数显示
        self._tbar_label = ttk_bs.Label(
            self.frame, text="当前位置: 0.00", bootstyle="info"
        )
        self._tbar_label.pack(anchor="w")

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=8)

        # Studio Mode
        ttk_bs.Label(self.frame, text="Studio 模式", font=FONT_BOLD).pack(anchor="w")
        studio_row = ttk_bs.Frame(self.frame)
        studio_row.pack(fill="x", pady=4)
        self._studio_btn = ttk_bs.Button(
            studio_row, text="开启 Studio 模式",
            bootstyle="info-outline", width=22,
            command=self._toggle_studio,
        )
        self._studio_btn.pack(side="left")
        self._studio_on = False

    # ── 刷新转场列表 ──────────────────────────────────────────

    def _load_transitions(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            self.root,
            ctrl.get_transition_list,
            self._on_transitions,
        )

    def _on_transitions(self, data) -> None:
        if isinstance(data, dict):
            transitions = data.get("transitions", [])
            current     = data.get("currentTransitionName", "")
        elif hasattr(data, "transitions"):
            transitions = data.transitions
            current     = getattr(data, "current_scene_transition_name", "")
        else:
            transitions = []
            current     = ""

        names = []
        for t in transitions:
            if isinstance(t, dict):
                names.append(t.get("transitionName", ""))
            elif hasattr(t, "transition_name"):
                names.append(t.transition_name)

        self._trans_cb["values"] = names
        if current in names:
            self._trans_var.set(current)
        elif names:
            self._trans_var.set(names[0])

    # ── 应用转场 ──────────────────────────────────────────────

    def _apply_transition(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        name     = self._trans_var.get()
        duration = self._duration_var.get()
        if name:
            self.app.log(f"转场设置: {name} / {duration}ms", "INFO")
            run_in_thread(
                self.root,
                lambda: (
                    ctrl.set_current_transition(name),
                    ctrl.set_transition_duration(duration),
                ),
            )

    # ── T-Bar ─────────────────────────────────────────────────

    def _on_tbar(self, val: str) -> None:
        v = float(val)
        self._tbar_label.config(text=f"当前位置: {v:.2f}")
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, lambda: ctrl.set_tbar_position(v))

    # ── Studio 模式 ───────────────────────────────────────────

    def _toggle_studio(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self._studio_on = not self._studio_on
        run_in_thread(
            self.root,
            lambda: ctrl.req.set_studio_mode_enabled(
                studio_mode_enabled=self._studio_on
            ),
            lambda _: self._update_studio_btn(),
        )

    def _update_studio_btn(self) -> None:
        if self._studio_on:
            self._studio_btn.config(
                text="关闭 Studio 模式", bootstyle="warning"
            )
            self.app.log("Studio 模式已开启", "INFO")
        else:
            self._studio_btn.config(
                text="开启 Studio 模式", bootstyle="info-outline"
            )
            self.app.log("Studio 模式已关闭", "INFO")

    # ── 供外部（App）调用 ─────────────────────────────────────

    def refresh(self) -> None:
        self._load_transitions()
