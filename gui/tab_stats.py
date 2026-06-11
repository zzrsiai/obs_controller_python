"""
gui/tab_stats.py  ——  统计 / 系统信息面板（右下角迷你面板模式）
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import run_in_thread, FONT_BIG, FONT_BOLD, FONT_LABEL, FONT_MONO

if TYPE_CHECKING:
    from .app import OBSGui


class _StatCard(ttk_bs.Labelframe):
    """单项统计卡片：大数字 + 单位标签。"""

    def __init__(self, parent: tk.Widget, title: str, unit: str = "", bootstyle: str = "primary"):
        super().__init__(parent, text=f" {title} ", bootstyle=bootstyle)
        self._var = tk.StringVar(value="--")
        ttk_bs.Label(self, textvariable=self._var, font=FONT_BIG).pack()
        if unit:
            ttk_bs.Label(self, text=unit, font=FONT_LABEL,
                         bootstyle="secondary").pack()

    def set(self, value: str) -> None:
        self._var.set(value)


class StatsTab:
    """统计/系统信息：嵌入右下角的紧凑统计面板。

    parent 可以是任意 Frame（不再要求 Notebook）。
    """

    def __init__(self, parent: tk.Widget, app: "OBSGui"):
        self.app = app
        self.root = app.root
        # 外层 Labelframe，可折叠感
        self.frame = ttk_bs.Labelframe(parent, text=" 📊 实时统计 ", padding=(6, 4))
        self.frame.pack(fill="x")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        # ── 第一行：统计卡片（紧凑，字体稍小） ──
        card_row = ttk_bs.Frame(self.frame)
        card_row.pack(fill="x", pady=(0, 4))

        self._fps_card  = self._mini_card(card_row, "FPS",  "success")
        self._cpu_card  = self._mini_card(card_row, "CPU%", "warning")
        self._mem_card  = self._mini_card(card_row, "MEM MB","info")
        self._disk_card = self._mini_card(card_row, "磁盘 GB","secondary")

        for i, card in enumerate([self._fps_card, self._cpu_card,
                                   self._mem_card, self._disk_card]):
            card.grid(row=0, column=i, padx=4, pady=2, sticky="ew")
            card_row.columnconfigure(i, weight=1)

        # ── 第二行：版本/平台信息 + 快照按钮 ──
        info_row = ttk_bs.Frame(self.frame)
        info_row.pack(fill="x", pady=(2, 0))

        # 版本信息（左侧，精简）
        ver_frame = ttk_bs.Frame(info_row)
        ver_frame.pack(side="left", fill="x", expand=True)

        self._ver_vars: dict[str, tk.StringVar] = {}
        for key, label in [("obsVersion", "OBS"), ("platform", "平台")]:
            row = ttk_bs.Frame(ver_frame)
            row.pack(fill="x", pady=0)
            ttk_bs.Label(row, text=f"{label}:", font=FONT_LABEL,
                         width=5, anchor="e").pack(side="left")
            var = tk.StringVar(value="--")
            self._ver_vars[key] = var
            ttk_bs.Label(row, textvariable=var, font=FONT_MONO,
                         bootstyle="info").pack(side="left", padx=4)

        # 也补充 obsWebSocketVersion（用于内部数据，不显示）
        self._ver_vars["obsWebSocketVersion"] = tk.StringVar(value="--")

        # 帧统计变量（轻量版，不渲染到界面，仅内部保留供扩展）
        self._frame_vars: dict[str, tk.StringVar] = {
            k: tk.StringVar(value="--")
            for k in ["totalFrames", "skippedFrames",
                      "renderSkippedFrames", "dropFrameRate"]
        }

        # 快照按钮（右侧）
        btn_frame = ttk_bs.Frame(info_row)
        btn_frame.pack(side="right")

        ttk_bs.Button(btn_frame, text="💾", bootstyle="primary-outline",
                      width=3, command=self._save_snapshot).pack(
            side="left", padx=2)
        ttk_bs.Button(btn_frame, text="📂", bootstyle="secondary-outline",
                      width=3, command=self._load_snapshot).pack(
            side="left", padx=2)

        self._snap_status = ttk_bs.Label(btn_frame, text="", bootstyle="success",
                                         font=FONT_LABEL)
        self._snap_status.pack(side="left", padx=4)

    def _mini_card(self, parent: tk.Widget, label: str, bootstyle: str) -> ttk_bs.Frame:
        """创建紧凑型统计卡（Label + 数值变量）。"""
        lf = ttk_bs.Labelframe(parent, text=f" {label} ", bootstyle=bootstyle)
        var = tk.StringVar(value="--")
        ttk_bs.Label(lf, textvariable=var,
                     font=("Segoe UI", 13, "bold")).pack(padx=4, pady=2)
        lf._var = var  # type: ignore[attr-defined]
        return lf

    # ── 刷新统计数据 ──────────────────────────────────────────

    def refresh(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, ctrl.get_stats, self._on_stats)
        run_in_thread(self.root, ctrl.get_version, self._on_version)

    def _on_stats(self, stats) -> None:
        def _get(obj, *keys):
            for k in keys:
                if isinstance(obj, dict):
                    v = obj.get(k)
                else:
                    v = getattr(obj, k, None)
                if v is not None:
                    return v
            return None

        fps  = _get(stats, "activeFps", "active_fps")
        cpu  = _get(stats, "cpuUsage",  "cpu_usage")
        mem  = _get(stats, "memoryUsage", "memory_usage")
        disk = _get(stats, "availableDiskSpace", "available_disk_space")

        self._fps_card._var.set(f"{fps:.1f}" if fps is not None else "--")  # type: ignore[attr-defined]
        self._cpu_card._var.set(f"{cpu:.1f}" if cpu is not None else "--")  # type: ignore[attr-defined]
        self._mem_card._var.set(f"{mem:.0f}" if mem is not None else "--")  # type: ignore[attr-defined]
        if disk is not None:
            self._disk_card._var.set(f"{disk/1024:.1f}")  # type: ignore[attr-defined]
        else:
            self._disk_card._var.set("--")  # type: ignore[attr-defined]

        # 帧数（内部变量，保留兼容性）
        total   = _get(stats, "outputTotalFrames",  "output_total_frames")  or 1
        skipped = _get(stats, "outputSkippedFrames","output_skipped_frames") or 0
        keys_map = {
            "totalFrames":         ("outputTotalFrames",  "output_total_frames"),
            "skippedFrames":       ("outputSkippedFrames","output_skipped_frames"),
            "renderSkippedFrames": ("renderSkippedFrames","render_skipped_frames"),
        }
        for key, src_keys in keys_map.items():
            val = _get(stats, *src_keys)
            self._frame_vars[key].set(str(val) if val is not None else "--")
        rate = (int(skipped) / int(total) * 100) if total else 0
        self._frame_vars["dropFrameRate"].set(f"{rate:.2f}%")

    def _on_version(self, ver) -> None:
        def _get(obj, *keys):
            for k in keys:
                if isinstance(obj, dict):
                    v = obj.get(k)
                else:
                    v = getattr(obj, k, None)
                if v is not None:
                    return v
            return "--"

        self._ver_vars["obsVersion"].set(
            _get(ver, "obsVersion", "obs_version"))
        self._ver_vars["obsWebSocketVersion"].set(
            _get(ver, "obsWebSocketVersion", "obs_web_socket_version"))
        self._ver_vars["platform"].set(
            _get(ver, "platform", "platform"))

    # ── 快照 ─────────────────────────────────────────────────

    def _save_snapshot(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        def do_save():
            self._snapshot = ctrl.snapshot_state()
        run_in_thread(
            self.root,
            do_save,
            lambda _: self._snap_status.config(text="✅ 已保存"),
        )

    def _load_snapshot(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        snapshot = getattr(self, "_snapshot", None)
        if snapshot is None:
            self._snap_status.config(text="⚠️ 先保存")
            return
        run_in_thread(
            self.root,
            lambda: ctrl.restore_state(snapshot),
            lambda _: self._snap_status.config(text="✅ 已恢复"),
        )
