"""
gui/tab_stats.py  ——  统计 / 系统信息标签页
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
    """统计/系统信息：大数字展示 + OBS 版本信息 + 状态快照。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self.frame = ttk_bs.Frame(notebook, padding=12)
        notebook.add(self.frame, text="📊 统计")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        ttk_bs.Label(self.frame, text="实时统计", font=FONT_BOLD).pack(
            anchor="w", pady=(0, 8)
        )

        # ── 统计卡片网格 ──
        grid = ttk_bs.Frame(self.frame)
        grid.pack(fill="x", pady=(0, 10))

        self._fps_card    = _StatCard(grid, "输出帧率",  "FPS",  "success")
        self._cpu_card    = _StatCard(grid, "CPU 使用", "%",     "warning")
        self._mem_card    = _StatCard(grid, "内存",     "MB",    "info")
        self._disk_card   = _StatCard(grid, "磁盘空间", "GB",    "secondary")

        for i, card in enumerate([self._fps_card, self._cpu_card,
                                   self._mem_card, self._disk_card]):
            card.grid(row=0, column=i, padx=8, pady=4, sticky="nsew")
            grid.columnconfigure(i, weight=1)

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=6)

        # ── 帧数/丢帧 ──
        frame_lf = ttk_bs.Labelframe(self.frame, text=" 帧数统计 ")
        frame_lf.pack(fill="x", pady=(0, 8))

        self._frame_vars: dict[str, tk.StringVar] = {}
        pairs = [
            ("总帧数",     "totalFrames"),
            ("跳帧数",     "skippedFrames"),
            ("渲染丢帧",   "renderSkippedFrames"),
            ("丢帧率",     "dropFrameRate"),
        ]
        for row_idx, (label, key) in enumerate(pairs):
            ttk_bs.Label(frame_lf, text=label + ":",
                         font=FONT_LABEL, width=14).grid(
                row=row_idx, column=0, sticky="w", pady=1
            )
            var = tk.StringVar(value="--")
            self._frame_vars[key] = var
            ttk_bs.Label(frame_lf, textvariable=var,
                         font=FONT_MONO, bootstyle="info").grid(
                row=row_idx, column=1, sticky="w", padx=8
            )

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=6)

        # ── OBS 版本信息 ──
        ver_lf = ttk_bs.Labelframe(self.frame, text=" 连接信息 ")
        ver_lf.pack(fill="x", pady=(0, 8))

        self._ver_vars: dict[str, tk.StringVar] = {}
        ver_pairs = [
            ("OBS 版本",        "obsVersion"),
            ("WebSocket 版本",  "obsWebSocketVersion"),
            ("平台",            "platform"),
        ]
        for row_idx, (label, key) in enumerate(ver_pairs):
            ttk_bs.Label(ver_lf, text=label + ":",
                         font=FONT_LABEL, width=16).grid(
                row=row_idx, column=0, sticky="w", pady=1
            )
            var = tk.StringVar(value="--")
            self._ver_vars[key] = var
            ttk_bs.Label(ver_lf, textvariable=var,
                         font=FONT_MONO, bootstyle="info").grid(
                row=row_idx, column=1, sticky="w", padx=8
            )

        # ── 状态快照 ──
        snap_lf = ttk_bs.Labelframe(self.frame, text=" 状态快照 ")
        snap_lf.pack(fill="x")

        snap_row = ttk_bs.Frame(snap_lf)
        snap_row.pack(fill="x")
        ttk_bs.Button(snap_row, text="💾 保存快照",
                      bootstyle="primary-outline",
                      command=self._save_snapshot).pack(side="left", padx=4)
        ttk_bs.Button(snap_row, text="📂 加载快照",
                      bootstyle="secondary-outline",
                      command=self._load_snapshot).pack(side="left", padx=4)

        self._snap_status = ttk_bs.Label(snap_lf, text="", bootstyle="success")
        self._snap_status.pack(anchor="w", pady=(4, 0))

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

        self._fps_card.set(f"{fps:.1f}" if fps is not None else "--")
        self._cpu_card.set(f"{cpu:.1f}" if cpu is not None else "--")
        self._mem_card.set(f"{mem:.0f}" if mem is not None else "--")
        if disk is not None:
            self._disk_card.set(f"{disk/1024:.1f}")
        else:
            self._disk_card.set("--")

        # 帧数
        keys_map = {
            "totalFrames":          ("outputTotalFrames",  "output_total_frames"),
            "skippedFrames":        ("outputSkippedFrames", "output_skipped_frames"),
            "renderSkippedFrames":  ("renderSkippedFrames", "render_skipped_frames"),
            "dropFrameRate":        ("outputSkippedFrames", "output_skipped_frames"),
        }
        total = _get(stats, "outputTotalFrames", "output_total_frames") or 1
        skipped = _get(stats, "outputSkippedFrames", "output_skipped_frames") or 0
        for key, src_keys in keys_map.items():
            val = _get(stats, *src_keys)
            if key == "dropFrameRate":
                rate = (skipped / total * 100) if total else 0
                self._frame_vars[key].set(f"{rate:.2f}%")
            else:
                self._frame_vars[key].set(str(val) if val is not None else "--")

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
        # snapshot_state() 返回快照 dict，保存到实例变量供后续还原使用
        def do_save():
            self._snapshot = ctrl.snapshot_state()
        run_in_thread(
            self.root,
            do_save,
            lambda _: self._snap_status.config(text="✅ 快照已保存"),
        )

    def _load_snapshot(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        snapshot = getattr(self, "_snapshot", None)
        if snapshot is None:
            self._snap_status.config(text="⚠️ 请先保存快照")
            return
        run_in_thread(
            self.root,
            lambda: ctrl.restore_state(snapshot),
            lambda _: self._snap_status.config(text="✅ 快照已恢复"),
        )
