"""
gui/tab_audio.py  ——  音频混音台标签页
每路音频：名称 | 音量滑块 | dB 显示 | 静音按钮 | VU 表
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import run_in_thread, FONT_BOLD, FONT_LABEL, CLR_GREEN, CLR_YELLOW, CLR_RED

if TYPE_CHECKING:
    from .app import OBSGui


# VU 表颜色阈值
VU_COLORS = [
    (-60, -18, CLR_GREEN),
    (-18,  -6, CLR_YELLOW),
    ( -6,   0, CLR_RED),
]

VU_W, VU_H = 120, 10   # VU 条尺寸


class AudioChannel:
    """单路音频 UI 行。"""

    def __init__(self, parent: tk.Widget, name: str, app: "OBSGui"):
        self.name = name
        self.app  = app
        self.root = app.root
        self._muted = False

        row = ttk_bs.Frame(parent, padding=(4, 2))
        row.pack(fill="x", pady=1)

        # 名称
        ttk_bs.Label(row, text=name[:22], width=22, font=FONT_LABEL).pack(
            side="left"
        )

        # 音量滑块 (-60 ~ 0 dB → 映射到 0~1 的 mul)
        self._vol_var = tk.DoubleVar(value=100.0)   # 0..100
        self._slider = ttk_bs.Scale(
            row, from_=0, to=100, orient="horizontal",
            variable=self._vol_var, length=160,
            command=self._on_volume,
        )
        self._slider.pack(side="left", padx=4)

        # dB 显示
        self._db_label = ttk_bs.Label(row, text="  0 dB", width=8, font=FONT_LABEL)
        self._db_label.pack(side="left")

        # 静音按钮
        self._mute_btn = ttk_bs.Button(
            row, text="🔊", width=3, bootstyle="secondary-outline",
            command=self._on_mute
        )
        self._mute_btn.pack(side="left", padx=4)

        # VU 表 Canvas
        self._vu = tk.Canvas(row, width=VU_W, height=VU_H,
                             bg="#1a1a1a", highlightthickness=0)
        self._vu.pack(side="left", padx=4)
        self._draw_vu(-60)

    # ── 回调 ─────────────────────────────────────────────────

    def _on_volume(self, val: str) -> None:
        v = float(val)
        # 0~100 → 0.0~1.0 mul
        mul = v / 100.0
        db  = 20 * (max(mul, 1e-6) ** (1/2)) - 60   # 近似 dB 显示
        db_str = f"{(v - 60):.0f} dB"
        self._db_label.config(text=db_str.rjust(7))
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, lambda: ctrl.set_input_volume(self.name, mul=mul))

    def _on_mute(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self._muted = not self._muted
        self._mute_btn.config(text="🔇" if self._muted else "🔊")
        run_in_thread(
            self.root,
            lambda: ctrl.set_input_mute(self.name, self._muted),
        )

    # ── VU 表 ────────────────────────────────────────────────

    def update_vu(self, db: float) -> None:
        """外部（主线程）调用，更新 VU 表。"""
        self._draw_vu(db)

    def _draw_vu(self, db: float) -> None:
        db = max(-60.0, min(0.0, db))
        ratio = (db + 60) / 60.0   # 0..1
        fill_w = int(VU_W * ratio)
        self._vu.delete("all")
        # 背景
        self._vu.create_rectangle(0, 0, VU_W, VU_H, fill="#1a1a1a", outline="")
        # 分段颜色
        x = 0
        for lo, hi, color in VU_COLORS:
            seg_ratio_lo = (lo + 60) / 60.0
            seg_ratio_hi = (hi + 60) / 60.0
            seg_x0 = int(VU_W * seg_ratio_lo)
            seg_x1 = int(VU_W * seg_ratio_hi)
            if fill_w > seg_x0:
                self._vu.create_rectangle(
                    seg_x0, 0, min(fill_w, seg_x1), VU_H,
                    fill=color, outline=""
                )

    def set_volume(self, mul: float) -> None:
        """外部更新滑块位置（0~1 mul）。"""
        self._vol_var.set(mul * 100)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._mute_btn.config(text="🔇" if muted else "🔊")


class AudioTab:
    """音频混音台标签页。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self._channels: dict[str, AudioChannel] = {}
        self.frame = ttk_bs.Frame(notebook, padding=8)
        notebook.add(self.frame, text="🎚 音频")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        # 顶部工具行
        top = ttk_bs.Frame(self.frame)
        top.pack(fill="x", pady=(0, 6))
        ttk_bs.Label(top, text="音频混音台", font=FONT_BOLD).pack(side="left")
        ttk_bs.Button(top, text="🔄 刷新", bootstyle="secondary-outline",
                      command=self.refresh).pack(side="right")

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=4)

        # 表头
        hdr = ttk_bs.Frame(self.frame, padding=(4, 0))
        hdr.pack(fill="x")
        for txt, w in [("输入源名称", 22), ("音量", 20), ("", 8), ("静音", 4), ("VU 表", 15)]:
            ttk_bs.Label(hdr, text=txt, width=w, font=FONT_LABEL).pack(side="left")

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=2)

        # 音频通道容器
        self._scroll_frame = ttk_bs.Frame(self.frame)
        self._scroll_frame.pack(fill="both", expand=True)
        self._container = self._scroll_frame

    # ── 刷新 ─────────────────────────────────────────────────

    def refresh(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, ctrl.get_audio_inputs, self._on_inputs_loaded)

    def _on_inputs_loaded(self, inputs: list) -> None:
        # 清空旧通道
        for w in self._container.winfo_children():
            w.destroy()
        self._channels.clear()

        for inp in inputs:
            name = inp if isinstance(inp, str) else inp.get("name", "")
            if not name:
                continue
            ch = AudioChannel(self._container, name, self.app)
            self._channels[name] = ch
            # 获取当前音量
            run_in_thread(
                self.root,
                lambda n=name: self.app.ctrl.get_input_volume(n),
                lambda vol, n=name: self._apply_volume(n, vol),
            )

    def _apply_volume(self, name: str, vol) -> None:
        ch = self._channels.get(name)
        if ch is None:
            return
        if isinstance(vol, dict):
            mul = vol.get("volume_mul", 1.0)
        elif hasattr(vol, "input_volume_mul"):
            mul = vol.input_volume_mul
        else:
            mul = 1.0
        ch.set_volume(mul)

    # ── 事件：VU 表更新（由 app 事件监听调用） ────────────────

    def update_vu(self, name: str, db: float) -> None:
        ch = self._channels.get(name)
        if ch:
            ch.update_vu(db)

    def update_mute(self, name: str, muted: bool) -> None:
        ch = self._channels.get(name)
        if ch:
            ch.set_muted(muted)
