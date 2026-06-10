"""
gui/tab_filter.py  ——  滤镜管理标签页
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs

from .utils import run_in_thread, FONT_BOLD

if TYPE_CHECKING:
    from .app import OBSGui


# 内置预设名称（与 obs_controller.py 中的 FILTER_PRESETS 对应）
PRESET_NAMES = [
    "美颜-轻度", "美颜-中度", "美颜-强度",
    "HDR感", "电影感", "夜间模式",
    "复古胶片", "高对比黑白",
]


class FilterTab:
    """滤镜管理：选择输入源 → 查看/启用/禁用/删除该源的滤镜 + 预设快速应用。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self.frame = ttk_bs.Frame(notebook, padding=10)
        notebook.add(self.frame, text="✨ 滤镜")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        # 顶部：输入源选择
        top = ttk_bs.Frame(self.frame)
        top.pack(fill="x", pady=(0, 6))
        ttk_bs.Label(top, text="输入源:").pack(side="left")
        self._src_var = tk.StringVar()
        self._src_cb = ttk_bs.Combobox(
            top, textvariable=self._src_var, width=28, state="readonly"
        )
        self._src_cb.pack(side="left", padx=6)
        self._src_cb.bind("<<ComboboxSelected>>", lambda _: self._load_filters())
        ttk_bs.Button(top, text="🔄", bootstyle="secondary-outline",
                      command=self._load_sources).pack(side="left")

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=4)

        # 中部：滤镜 Treeview
        ttk_bs.Label(self.frame, text="该源的滤镜列表", font=FONT_BOLD).pack(anchor="w")

        tree_frame = ttk_bs.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, pady=4)

        cols = ("滤镜名称", "类型", "启用")
        self._tree = ttk_bs.Treeview(
            tree_frame, columns=cols, show="headings", height=9,
            bootstyle="dark"
        )
        for c in cols:
            self._tree.heading(c, text=c)
        self._tree.column("滤镜名称", width=160)
        self._tree.column("类型",     width=120)
        self._tree.column("启用",     width=60, anchor="center")

        vsb = ttk_bs.Scrollbar(tree_frame, orient="vertical",
                               command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        # 操作按钮
        btn_row = ttk_bs.Frame(self.frame)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk_bs.Button(btn_row, text="启用/禁用", bootstyle="warning",
                      command=self._toggle_filter).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="删除滤镜", bootstyle="danger-outline",
                      command=self._delete_filter).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="🔄 刷新", bootstyle="secondary-outline",
                      command=self._load_filters).pack(side="right", padx=2)

        ttk_bs.Separator(self.frame, orient="horizontal").pack(fill="x", pady=8)

        # 底部：预设快速应用
        ttk_bs.Label(self.frame, text="预设快速应用", font=FONT_BOLD).pack(anchor="w")
        preset_row = ttk_bs.Frame(self.frame)
        preset_row.pack(fill="x", pady=4)
        ttk_bs.Label(preset_row, text="预设名称:").pack(side="left")
        self._preset_var = tk.StringVar(value=PRESET_NAMES[0])
        ttk_bs.Combobox(
            preset_row, textvariable=self._preset_var,
            values=PRESET_NAMES, width=20, state="readonly"
        ).pack(side="left", padx=6)
        ttk_bs.Button(preset_row, text="应用预设", bootstyle="primary",
                      command=self._apply_preset).pack(side="left")

    # ── 加载输入源列表 ────────────────────────────────────────

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
        self._src_cb["values"] = names
        if names:
            self._src_var.set(names[0])
            self._load_filters()

    # ── 加载滤镜列表 ──────────────────────────────────────────

    def _load_filters(self) -> None:
        src = self._src_var.get()
        if not src:
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            self.root,
            lambda: ctrl.get_filter_list(src),
            self._on_filters,
        )

    def _on_filters(self, filters) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        items = filters if isinstance(filters, list) else getattr(filters, "filters", [])
        for f in items:
            if isinstance(f, dict):
                name    = f.get("filterName", "")
                kind    = f.get("filterKind", "")
                enabled = "✓" if f.get("filterEnabled", True) else "✗"
            else:
                name    = getattr(f, "filter_name", "")
                kind    = getattr(f, "filter_kind", "")
                enabled = "✓" if getattr(f, "filter_enabled", True) else "✗"
            self._tree.insert("", "end", iid=name, values=(name, kind, enabled))

    # ── 启用/禁用 ─────────────────────────────────────────────

    def _toggle_filter(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        filter_name = sel[0]
        src = self._src_var.get()
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        vals = self._tree.item(sel[0], "values")
        new_enabled = (vals[2] != "✓")
        run_in_thread(
            self.root,
            lambda: ctrl.set_filter_enabled(src, filter_name, new_enabled),
            lambda _: self._load_filters(),
        )

    # ── 删除滤镜 ──────────────────────────────────────────────

    def _delete_filter(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        filter_name = sel[0]
        src = self._src_var.get()
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        if not messagebox.askyesno("删除滤镜", f"确认删除滤镜「{filter_name}」？"):
            return
        run_in_thread(
            self.root,
            lambda: ctrl.remove_filter(src, filter_name),
            lambda _: self._load_filters(),
        )

    # ── 预设应用 ──────────────────────────────────────────────

    def _apply_preset(self) -> None:
        src    = self._src_var.get()
        preset = self._preset_var.get()
        ctrl   = self.app.ctrl
        if ctrl is None or not src or not preset:
            return
        run_in_thread(
            self.root,
            lambda: ctrl.apply_filter_preset(src, preset),
            lambda _: self._load_filters(),
        )

    # ── 刷新入口 ──────────────────────────────────────────────

    def refresh(self) -> None:
        self._load_sources()
