"""
gui/tab_replay.py  ——  回放缓冲 + 截图标签页
"""
from __future__ import annotations
import io
import base64
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs
from PIL import Image, ImageTk

from .utils import run_in_thread, FONT_BOLD, FONT_LABEL

if TYPE_CHECKING:
    from .app import OBSGui


THUMB_W, THUMB_H = 256, 144   # 截图缩略图尺寸


class ReplayTab:
    """回放缓冲控制 + 截图功能。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self._replay_on   = False
        self._thumb_photo: ImageTk.PhotoImage | None = None

        self.frame = ttk_bs.Frame(notebook, padding=10)
        notebook.add(self.frame, text="📼 回放/截图")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        # ── 回放缓冲 ──
        buf_lf = ttk_bs.Labelframe(self.frame, text=" 📼 回放缓冲 ")
        buf_lf.pack(fill="x", pady=(0, 10))

        b1 = ttk_bs.Frame(buf_lf)
        b1.pack(fill="x")
        self._buf_btn = ttk_bs.Button(
            b1, text="▶ 启动缓冲", bootstyle="success", width=14,
            command=self._toggle_replay,
        )
        self._buf_btn.pack(side="left", padx=(0, 8))

        ttk_bs.Button(
            b1, text="💾 保存回放", bootstyle="primary-outline", width=14,
            command=self._save_replay,
        ).pack(side="left")

        b2 = ttk_bs.Frame(buf_lf)
        b2.pack(fill="x", pady=(6, 0))
        ttk_bs.Label(b2, text="最近保存:").pack(side="left")
        self._saved_path_var = tk.StringVar(value="（未保存）")
        ttk_bs.Label(b2, textvariable=self._saved_path_var,
                     bootstyle="info", font=FONT_LABEL).pack(side="left", padx=6)

        # ── 截图 ──
        shot_lf = ttk_bs.Labelframe(self.frame, text=" 📷 截图 ")
        shot_lf.pack(fill="x")

        s1 = ttk_bs.Frame(shot_lf)
        s1.pack(fill="x", pady=(0, 6))

        ttk_bs.Label(s1, text="输入源:").pack(side="left")
        self._shot_src_var = tk.StringVar()
        self._shot_src_cb = ttk_bs.Combobox(
            s1, textvariable=self._shot_src_var, width=22, state="readonly"
        )
        self._shot_src_cb.pack(side="left", padx=6)
        ttk_bs.Button(s1, text="🔄", bootstyle="secondary-outline",
                      command=self._load_sources).pack(side="left")

        s2 = ttk_bs.Frame(shot_lf)
        s2.pack(fill="x", pady=(0, 6))
        ttk_bs.Label(s2, text="格式:").pack(side="left")
        self._fmt_var = tk.StringVar(value="jpg")
        ttk_bs.Combobox(
            s2, textvariable=self._fmt_var,
            values=["jpg", "png", "webp", "bmp"],
            width=8, state="readonly"
        ).pack(side="left", padx=6)
        ttk_bs.Label(s2, text="质量:").pack(side="left")
        self._quality_var = tk.IntVar(value=85)
        ttk_bs.Scale(
            s2, from_=1, to=100, orient="horizontal",
            variable=self._quality_var, length=120,
        ).pack(side="left", padx=4)
        self._quality_lbl = ttk_bs.Label(s2, text="85", width=4)
        self._quality_lbl.pack(side="left")
        self._quality_var.trace_add(
            "write",
            lambda *_: self._quality_lbl.config(text=str(self._quality_var.get()))
        )

        ttk_bs.Button(
            shot_lf, text="📸 立即截图", bootstyle="primary", width=16,
            command=self._take_screenshot,
        ).pack(anchor="w", pady=4)

        # 缩略图显示
        self._thumb_canvas = tk.Canvas(
            shot_lf, width=THUMB_W, height=THUMB_H,
            bg="#1a1a1a", highlightthickness=1, highlightbackground="#444"
        )
        self._thumb_canvas.pack(pady=4)
        self._thumb_canvas.create_text(
            THUMB_W // 2, THUMB_H // 2,
            text="截图预览", fill="#555", tags="placeholder"
        )

    # ── 回放缓冲控制 ──────────────────────────────────────────

    def _toggle_replay(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._replay_on:
            run_in_thread(self.root, ctrl.start_replay_buffer,
                          lambda _: self._set_replay(True))
        else:
            run_in_thread(self.root, ctrl.stop_replay_buffer,
                          lambda _: self._set_replay(False))

    def _set_replay(self, on: bool) -> None:
        self._replay_on = on
        self._buf_btn.config(
            text="⏹ 停止缓冲" if on else "▶ 启动缓冲",
            bootstyle="danger" if on else "success",
        )

    def _save_replay(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            self.root,
            ctrl.save_replay_buffer,
            lambda res: self._on_replay_saved(res),
        )

    def _on_replay_saved(self, res) -> None:
        if isinstance(res, dict):
            path = res.get("savedReplayPath", "")
        elif hasattr(res, "saved_replay_path"):
            path = res.saved_replay_path
        else:
            path = str(res)
        self._saved_path_var.set(path or "（已保存）")

    # ── 截图 ─────────────────────────────────────────────────

    def _load_sources(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, ctrl.get_input_list, self._on_sources)

    def _on_sources(self, inputs: list) -> None:
        names = []
        for inp in inputs:
            n = inp if isinstance(inp, str) else inp.get("name", "")
            if n:
                names.append(n)
        self._shot_src_cb["values"] = names
        # 也尝试加载当前场景名
        try:
            scene = self.app.ctrl.get_current_scene()
            if scene and scene not in names:
                names.insert(0, scene)
                self._shot_src_cb["values"] = names
        except Exception:
            pass
        if names:
            self._shot_src_var.set(names[0])

    def _take_screenshot(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        src     = self._shot_src_var.get()
        fmt     = self._fmt_var.get()
        quality = self._quality_var.get()
        if not src:
            return
        run_in_thread(
            self.root,
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
            raw   = base64.b64decode(b64)
            img   = Image.open(io.BytesIO(raw)).resize(
                (THUMB_W, THUMB_H), Image.BILINEAR
            )
            photo = ImageTk.PhotoImage(img)
            self._thumb_canvas.delete("all")
            self._thumb_canvas.create_image(0, 0, anchor="nw", image=photo)
            self._thumb_photo = photo  # 保持引用
        except Exception:
            pass

    # ── 刷新入口 ──────────────────────────────────────────────

    def refresh(self) -> None:
        self._load_sources()
