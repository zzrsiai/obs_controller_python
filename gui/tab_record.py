"""
gui/tab_record.py  ——  录制 / 推流 / 虚拟摄像头 标签页（PyQt5 版）
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QGroupBox,
)
from PyQt5.QtCore import Qt

from .utils import run_in_thread, FONT_BOLD, FONT_LABEL, FONT_MONO, CLR_GREEN, CLR_RED

if TYPE_CHECKING:
    from .app import OBSGui


class RecordTab(QWidget):
    """录制、推流、虚拟摄像头、字幕控制。"""

    def __init__(self, parent, app: "OBSGui"):
        super().__init__(parent)
        self.app = app
        self._recording = False
        self._streaming = False
        self._vcam_on = False
        self._rec_paused = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── 录制区 ──
        rec_group = QGroupBox(" 🎥 录制 ")
        rec_layout = QVBoxLayout(rec_group)

        r1 = QHBoxLayout()
        self._rec_btn = QPushButton("▶ 开始录制")
        self._rec_btn.setProperty("success", True)
        self._rec_btn.setFixedWidth(130)
        self._rec_btn.clicked.connect(self._toggle_record)
        r1.addWidget(self._rec_btn)

        self._rec_pause_btn = QPushButton("⏸ 暂停")
        self._rec_pause_btn.setProperty("warning", True)
        self._rec_pause_btn.setFixedWidth(80)
        self._rec_pause_btn.clicked.connect(self._toggle_pause)
        self._rec_pause_btn.setEnabled(False)
        r1.addWidget(self._rec_pause_btn)

        r1.addSpacing(16)
        r1.addWidget(QLabel("时码:"))
        self._rec_tc = QLabel("--:--:--")
        self._rec_tc.setStyleSheet(f"color: {CLR_GREEN}; font-family: Consolas;")
        r1.addWidget(self._rec_tc)
        r1.addStretch()
        rec_layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("录制目录:"))
        self._rec_dir_edit = QLineEdit("（默认）")
        self._rec_dir_edit.setFixedWidth(300)
        r2.addWidget(self._rec_dir_edit)
        btn_apply = QPushButton("应用")
        btn_apply.setProperty("outline", True)
        btn_apply.clicked.connect(self._set_rec_dir)
        r2.addWidget(btn_apply)
        r2.addStretch()
        rec_layout.addLayout(r2)

        layout.addWidget(rec_group)

        # ── 推流区 ──
        stream_group = QGroupBox(" 📡 推流 ")
        stream_layout = QVBoxLayout(stream_group)

        s1 = QHBoxLayout()
        self._stream_btn = QPushButton("▶ 开始推流")
        self._stream_btn.setFixedWidth(130)
        self._stream_btn.clicked.connect(self._toggle_stream)
        s1.addWidget(self._stream_btn)

        s1.addSpacing(16)
        s1.addWidget(QLabel("时码:"))
        self._stream_tc = QLabel("--:--:--")
        self._stream_tc.setStyleSheet(f"color: {CLR_GREEN}; font-family: Consolas;")
        s1.addWidget(self._stream_tc)
        s1.addStretch()
        stream_layout.addLayout(s1)

        s2 = QHBoxLayout()
        s2.addWidget(QLabel("推流服务器:"))
        self._stream_url = QLineEdit()
        self._stream_url.setFixedWidth(240)
        s2.addWidget(self._stream_url)

        s2.addWidget(QLabel("密钥:"))
        self._stream_key = QLineEdit()
        self._stream_key.setFixedWidth(140)
        self._stream_key.setEchoMode(QLineEdit.Password)
        s2.addWidget(self._stream_key)

        btn_save = QPushButton("保存")
        btn_save.setProperty("outline", True)
        btn_save.clicked.connect(self._save_stream_settings)
        s2.addWidget(btn_save)
        s2.addStretch()
        stream_layout.addLayout(s2)

        layout.addWidget(stream_group)

        # ── 虚拟摄像头 ──
        vcam_group = QGroupBox(" 📷 虚拟摄像头 ")
        vcam_layout = QHBoxLayout(vcam_group)

        self._vcam_btn = QPushButton("▶ 开启虚拟摄像头")
        self._vcam_btn.setProperty("outline", True)
        self._vcam_btn.setFixedWidth(180)
        self._vcam_btn.clicked.connect(self._toggle_vcam)
        vcam_layout.addWidget(self._vcam_btn)
        vcam_layout.addStretch()

        layout.addWidget(vcam_group)

        # ── 字幕 ──
        caption_group = QGroupBox(" 💬 字幕 ")
        caption_layout = QHBoxLayout(caption_group)

        self._caption_edit = QLineEdit()
        self._caption_edit.setFixedWidth(340)
        caption_layout.addWidget(self._caption_edit)

        btn_send = QPushButton("发送")
        btn_send.clicked.connect(self._send_caption)
        caption_layout.addWidget(btn_send)
        caption_layout.addStretch()

        layout.addWidget(caption_group)
        layout.addStretch()

    # ── 录制控制 ──────────────────────────────────────────────

    def _toggle_record(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._recording:
            run_in_thread(ctrl.start_record, lambda _: self._set_recording(True))
        else:
            run_in_thread(ctrl.stop_record, lambda _: self._set_recording(False))

    def _toggle_pause(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._rec_paused:
            run_in_thread(ctrl.pause_record, lambda _: self._set_paused(True))
        else:
            run_in_thread(ctrl.resume_record, lambda _: self._set_paused(False))

    def _set_recording(self, active: bool) -> None:
        self._recording = active
        if active:
            self._rec_btn.setText("⏹ 停止录制")
            self._rec_btn.setProperty("danger", True)
            self._rec_btn.style().polish(self._rec_btn)
            self._rec_pause_btn.setEnabled(True)
            self.app.log("录制已开始", "SUCCESS")
        else:
            self._rec_btn.setText("▶ 开始录制")
            self._rec_btn.setProperty("success", True)
            self._rec_btn.style().polish(self._rec_btn)
            self._rec_pause_btn.setEnabled(False)
            self._rec_pause_btn.setText("⏸ 暂停")
            self._rec_tc.setText("--:--:--")
            self._rec_paused = False
            self.app.log("录制已停止", "INFO")

    def _set_paused(self, paused: bool) -> None:
        self._rec_paused = paused
        self._rec_pause_btn.setText("▶ 继续" if paused else "⏸ 暂停")
        self.app.log("录制已暂停" if paused else "录制已恢复", "WARNING" if paused else "INFO")

    def _set_rec_dir(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        path = self._rec_dir_edit.text().strip()
        if not path or path == "（默认）":
            return
        run_in_thread(lambda: ctrl.set_record_directory(path))

    def update_rec_timecode(self, tc: str) -> None:
        self._rec_tc.setText(tc)

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
            run_in_thread(ctrl.start_stream, lambda _: self._set_streaming(True))
        else:
            run_in_thread(ctrl.stop_stream, lambda _: self._set_streaming(False))

    def _set_streaming(self, active: bool) -> None:
        self._streaming = active
        if active:
            self._stream_btn.setText("⏹ 停止推流")
            self._stream_btn.setProperty("danger", True)
            self._stream_btn.style().polish(self._stream_btn)
            self.app.log("推流已开始", "SUCCESS")
        else:
            self._stream_btn.setText("▶ 开始推流")
            self._stream_btn.setProperty("success", True)
            self._stream_btn.style().polish(self._stream_btn)
            self._stream_tc.setText("--:--:--")
            self.app.log("推流已停止", "INFO")

    def _save_stream_settings(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        server = self._stream_url.text().strip()
        key = self._stream_key.text().strip()
        if server:
            run_in_thread(
                lambda: ctrl.set_stream_service_settings(
                    service_type="rtmp_common",
                    service_settings={"server": server, "key": key},
                ),
            )

    def update_stream_timecode(self, tc: str) -> None:
        self._stream_tc.setText(tc)

    def set_streaming_state(self, active: bool) -> None:
        self._set_streaming(active)

    # ── 虚拟摄像头 ────────────────────────────────────────────

    def _toggle_vcam(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not self._vcam_on:
            run_in_thread(ctrl.start_virtualcam, lambda _: self._set_vcam(True))
        else:
            run_in_thread(ctrl.stop_virtualcam, lambda _: self._set_vcam(False))

    def _set_vcam(self, on: bool) -> None:
        self._vcam_on = on
        self._vcam_btn.setText("⏹ 关闭虚拟摄像头" if on else "▶ 开启虚拟摄像头")
        if on:
            self._vcam_btn.setProperty("danger", True)
        else:
            self._vcam_btn.setProperty("outline", True)
        self._vcam_btn.style().polish(self._vcam_btn)
        self.app.log("虚拟摄像头已开启" if on else "虚拟摄像头已关闭", "INFO")

    # ── 字幕 ─────────────────────────────────────────────────

    def _send_caption(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        text = self._caption_edit.text().strip()
        if text:
            run_in_thread(lambda: ctrl.send_stream_caption(text))
