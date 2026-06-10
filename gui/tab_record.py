"""
gui/tab_record.py  ——  录制 / 推流 / 虚拟摄像头 标签页
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import run_in_thread, FONT_BOLD, FONT_LABEL, FONT_MONO, CLR_GREEN, CLR_RED

if TYPE_CHECKING:
    from .app import OBSGui


class RecordTab:
    """录制、推流、虚拟摄像头、字幕控制。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self._recording = False
        self._streaming = False
        self._vcam_on   = False
        self._rec_paused = False

        self.frame = ttk_bs.Frame(notebook, padding=10)
        notebook.add(self.frame, text="⏺ 录制/推流")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        # ── 录制区 ──
        rec_lf = ttk_bs.Labelframe(self.frame, text=" 🎥 录制 ")
        rec_lf.pack(fill="x", pady=(0, 8))

        r1 = ttk_bs.Frame(rec_lf)
        r1.pack(fill="x")
        self._rec_btn = ttk_bs.Button(
            r1, text="▶ 开始录制", bootstyle="success", width=14,
            command=self._toggle_record
        )
        self._rec_btn.pack(side="left", padx=(0, 6))

        self._rec_pause_btn = ttk_bs.Button(
            r1, text="⏸ 暂停", bootstyle="warning-outline", width=8,
            command=self._toggle_pause, state="disabled"
        )
        self._rec_pause_btn.pack(side="left", padx=4)

        ttk_bs.Label(r1, text="时码:").pack(side="left", padx=(16, 4))
        self._rec_tc = ttk_bs.Label(r1, text="--:--:--",
                                    font=FONT_MONO, bootstyle="info")
        self._rec_tc.pack(side="left")

        r2 = ttk_bs.Frame(rec_lf)
        r2.pack(fill="x", pady=(6, 0))
        ttk_bs.Label(r2, text="录制目录:").pack(side="left")
        self._rec_dir_var = tk.StringVar(value="（默认）")
        ttk_bs.Entry(r2, textvariable=self._rec_dir_var, width=36).pack(
            side="left", padx=6
        )
        ttk_bs.Button(r2, text="应用", bootstyle="secondary-outline",
                      command=self._set_rec_dir).pack(side="left")

        # ── 推流区 ──
        stream_lf = ttk_bs.Labelframe(self.frame, text=" 📡 推流 ")
        stream_lf.pack(fill="x", pady=(0, 8))

        s1 = ttk_bs.Frame(stream_lf)
        s1.pack(fill="x")
        self._stream_btn = ttk_bs.Button(
            s1, text="▶ 开始推流", bootstyle="primary", width=14,
            command=self._toggle_stream
        )
        self._stream_btn.pack(side="left", padx=(0, 6))

        ttk_bs.Label(s1, text="时码:").pack(side="left", padx=(16, 4))
        self._stream_tc = ttk_bs.Label(s1, text="--:--:--",
                                       font=FONT_MONO, bootstyle="info")
        self._stream_tc.pack(side="left")

        s2 = ttk_bs.Frame(stream_lf)
        s2.pack(fill="x", pady=(6, 0))
        ttk_bs.Label(s2, text="推流服务器:").pack(side="left")
        self._stream_url = tk.StringVar()
        ttk_bs.Entry(s2, textvariable=self._stream_url, width=30).pack(
            side="left", padx=4
        )
        ttk_bs.Label(s2, text="密钥:").pack(side="left")
        self._stream_key = tk.StringVar()
        ttk_bs.Entry(s2, textvariable=self._stream_key, width=16, show="*").pack(
            side="left", padx=4
        )
        ttk_bs.Button(s2, text="保存", bootstyle="secondary-outline",
                      command=self._save_stream_settings).pack(side="left")

        # ── 虚拟摄像头 ──
        vcam_lf = ttk_bs.Labelframe(self.frame, text=" 📷 虚拟摄像头 ")
        vcam_lf.pack(fill="x", pady=(0, 8))

        self._vcam_btn = ttk_bs.Button(
            vcam_lf, text="▶ 开启虚拟摄像头",
            bootstyle="info-outline", width=20,
            command=self._toggle_vcam
        )
        self._vcam_btn.pack(side="left")

        # ── 字幕 ──
        caption_lf = ttk_bs.Labelframe(self.frame, text=" 💬 字幕 ")
        caption_lf.pack(fill="x")

        cap_row = ttk_bs.Frame(caption_lf)
        cap_row.pack(fill="x")
        self._caption_var = tk.StringVar()
        ttk_bs.Entry(cap_row, textvariable=self._caption_var, width=40).pack(
            side="left", padx=(0, 6)
        )
        ttk_bs.Button(cap_row, text="发送", bootstyle="primary",
                      command=self._send_caption).pack(side="left")

    # ── 录制控制 ──────────────────────────────────────────────

    def _toggle_record(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._recording:
            run_in_thread(self.root, ctrl.start_record,
                          lambda _: self._set_recording(True))
        else:
            run_in_thread(self.root, ctrl.stop_record,
                          lambda _: self._set_recording(False))

    def _toggle_pause(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._rec_paused:
            run_in_thread(self.root, ctrl.pause_record,
                          lambda _: self._set_paused(True))
        else:
            run_in_thread(self.root, ctrl.resume_record,
                          lambda _: self._set_paused(False))

    def _set_recording(self, active: bool) -> None:
        self._recording = active
        if active:
            self._rec_btn.config(text="⏹ 停止录制", bootstyle="danger")
            self._rec_pause_btn.config(state="normal")
            self.app.log("录制已开始", "SUCCESS")
        else:
            self._rec_btn.config(text="▶ 开始录制", bootstyle="success")
            self._rec_pause_btn.config(state="disabled", text="⏸ 暂停")
            self._rec_tc.config(text="--:--:--")
            self._rec_paused = False
            self.app.log("录制已停止", "INFO")

    def _set_paused(self, paused: bool) -> None:
        self._rec_paused = paused
        self._rec_pause_btn.config(
            text="▶ 继续" if paused else "⏸ 暂停"
        )
        self.app.log("录制已暂停" if paused else "录制已恢复", "WARNING" if paused else "INFO")

    def _set_rec_dir(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        path = self._rec_dir_var.get().strip()
        if not path or path == "（默认）":
            return
        run_in_thread(self.root, lambda: ctrl.set_record_directory(path))

    def update_rec_timecode(self, tc: str) -> None:
        self._rec_tc.config(text=tc)

    def set_recording_state(self, active: bool, paused: bool = False) -> None:
        self._set_recording(active)
        if active and paused:
            self._set_paused(paused)

    # ── 推流控制 ──────────────────────────────────────────────

    def _toggle_stream(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._streaming:
            run_in_thread(self.root, ctrl.start_stream,
                          lambda _: self._set_streaming(True))
        else:
            run_in_thread(self.root, ctrl.stop_stream,
                          lambda _: self._set_streaming(False))

    def _set_streaming(self, active: bool) -> None:
        self._streaming = active
        if active:
            self._stream_btn.config(text="⏹ 停止推流", bootstyle="danger")
            self.app.log("推流已开始", "SUCCESS")
        else:
            self._stream_btn.config(text="▶ 开始推流", bootstyle="primary")
            self._stream_tc.config(text="--:--:--")
            self.app.log("推流已停止", "INFO")

    def _save_stream_settings(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        server = self._stream_url.get().strip()
        key    = self._stream_key.get().strip()
        if server:
            run_in_thread(
                self.root,
                lambda: ctrl.set_stream_service_settings(
                    service_type="rtmp_common",
                    service_settings={"server": server, "key": key},
                ),
            )

    def update_stream_timecode(self, tc: str) -> None:
        self._stream_tc.config(text=tc)

    def set_streaming_state(self, active: bool) -> None:
        self._set_streaming(active)

    # ── 虚拟摄像头 ────────────────────────────────────────────

    def _toggle_vcam(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._vcam_on:
            run_in_thread(self.root, ctrl.start_virtualcam,
                          lambda _: self._set_vcam(True))
        else:
            run_in_thread(self.root, ctrl.stop_virtualcam,
                          lambda _: self._set_vcam(False))

    def _set_vcam(self, on: bool) -> None:
        self._vcam_on = on
        self._vcam_btn.config(
            text="⏹ 关闭虚拟摄像头" if on else "▶ 开启虚拟摄像头",
            bootstyle="danger" if on else "info-outline",
        )
        self.app.log("虚拟摄像头已开启" if on else "虚拟摄像头已关闭", "INFO")

    # ── 字幕 ─────────────────────────────────────────────────

    def _send_caption(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        text = self._caption_var.get().strip()
        if text:
            run_in_thread(self.root, lambda: ctrl.send_stream_caption(text))
