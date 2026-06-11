"""
gui/tab_scene.py  ——  场景管理标签页
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import TYPE_CHECKING

import ttkbootstrap as ttk_bs
from ttkbootstrap.constants import *

from .utils import run_in_thread, FONT_BOLD

if TYPE_CHECKING:
    from .app import OBSGui


class SceneTab:
    """场景管理：左侧场景列表，右侧场景项 Treeview。"""

    def __init__(self, notebook: ttk_bs.Notebook, app: "OBSGui"):
        self.app = app
        self.root = app.root
        self.frame = ttk_bs.Frame(notebook, padding=8)
        notebook.add(self.frame, text="🎬 场景")
        self._build()

    # ── 构建 ─────────────────────────────────────────────────

    def _build(self) -> None:
        paned = ttk_bs.Panedwindow(self.frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ─ 左列：场景列表 ─
        left = ttk_bs.Frame(paned, padding=4)
        paned.add(left, weight=1)

        ttk_bs.Label(left, text="场景列表", font=FONT_BOLD).pack(anchor="w")

        list_frame = ttk_bs.Frame(left)
        list_frame.pack(fill="both", expand=True, pady=4)

        sb = ttk_bs.Scrollbar(list_frame, orient="vertical")
        self.scene_list = tk.Listbox(
            list_frame,
            yscrollcommand=sb.set,
            selectmode="single",
            bg="#2b2b2b", fg="#ffffff",
            selectbackground="#375a7f",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
        )
        sb.config(command=self.scene_list.yview)
        sb.pack(side="right", fill="y")
        self.scene_list.pack(fill="both", expand=True)

        self.scene_list.bind("<Double-1>", self._on_scene_dbl)
        self.scene_list.bind("<Button-3>", self._show_context_menu)
        self.scene_list.bind("<<ListboxSelect>>", self._on_scene_select)

        # 操作按钮行
        btn_row = ttk_bs.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk_bs.Button(btn_row, text="切换", bootstyle="primary",
                      command=self._switch_scene).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="新建", bootstyle="success-outline",
                      command=self._create_scene).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="删除", bootstyle="danger-outline",
                      command=self._delete_scene).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="重命名", bootstyle="warning-outline",
                      command=self._rename_scene).pack(side="left", padx=2)
        ttk_bs.Button(btn_row, text="🔄", bootstyle="secondary-outline",
                      command=self.refresh).pack(side="right", padx=2)

        # ─ 右列：场景项列表 ─
        right = ttk_bs.Frame(paned, padding=4)
        paned.add(right, weight=2)

        ttk_bs.Label(right, text="场景项（单击场景查看）", font=FONT_BOLD).pack(anchor="w")

        tree_frame = ttk_bs.Frame(right)
        tree_frame.pack(fill="both", expand=True, pady=4)

        cols = ("名称", "类型", "启用")
        self.item_tree = ttk_bs.Treeview(
            tree_frame, columns=cols, show="headings", height=12,
            bootstyle="dark"
        )
        for c in cols:
            self.item_tree.heading(c, text=c)
        self.item_tree.column("名称", width=160)
        self.item_tree.column("类型", width=90)
        self.item_tree.column("启用", width=60, anchor="center")

        vsb = ttk_bs.Scrollbar(tree_frame, orient="vertical",
                               command=self.item_tree.yview)
        self.item_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.item_tree.pack(fill="both", expand=True)

        # 场景项操作
        item_btns = ttk_bs.Frame(right)
        item_btns.pack(fill="x", pady=(4, 0))
        ttk_bs.Button(item_btns, text="启用/禁用", bootstyle="warning",
                      command=self._toggle_item).pack(side="left", padx=2)
        ttk_bs.Button(item_btns, text="删除项", bootstyle="danger-outline",
                      command=self._delete_item).pack(side="left", padx=2)

        # 右键菜单
        self._ctx_menu = tk.Menu(self.root, tearoff=0)
        self._ctx_menu.add_command(label="切换到此场景", command=self._switch_scene)
        self._ctx_menu.add_command(label="重命名", command=self._rename_scene)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="删除", command=self._delete_scene)

    # ── 刷新 ─────────────────────────────────────────────────

    def refresh(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(self.root, ctrl.get_scene_names, self._on_scenes_loaded)

    def _on_scenes_loaded(self, scenes: list) -> None:
        self.scene_list.delete(0, "end")
        for s in scenes:
            name = s if isinstance(s, str) else s.get("sceneName", "")
            self.scene_list.insert("end", name)
        # 异步获取当前场景并选中（避免主线程阻塞）
        ctrl = self.app.ctrl
        if ctrl:
            run_in_thread(
                self.root,
                ctrl.get_current_scene,
                lambda cur: self._select_scene(cur),
            )

    def _select_scene(self, current: str) -> None:
        """异步回调：在列表中高亮当前场景。"""
        for i in range(self.scene_list.size()):
            if self.scene_list.get(i) == current:
                self.scene_list.selection_set(i)
                self.scene_list.see(i)
                break

    def load_items(self, scene_name: str) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            self.root,
            lambda: ctrl.get_scene_items(scene_name),
            self._on_items_loaded,
        )

    def _on_items_loaded(self, items: list) -> None:
        for row in self.item_tree.get_children():
            self.item_tree.delete(row)
        for item in items:
            name    = item.get("source_name", "")
            kind    = item.get("source_type", "")
            enabled = "✓" if item.get("enabled", True) else "✗"
            self.item_tree.insert(
                "", "end",
                iid=str(item.get("scene_item_id", "")),
                values=(name, kind, enabled),
            )

    # ── 事件回调 ──────────────────────────────────────────────

    def _on_scene_dbl(self, _event) -> None:
        """双击场景：切换到该场景。"""
        self._switch_scene()

    def _on_scene_select(self, _event) -> None:
        """单击选中场景：显示预览截图 + 加载场景项列表。
        使用 after_idle 延迟，因为 <<ListboxSelect>> 在选择状态更新前触发。"""
        self.root.after_idle(self._do_scene_select)

    def _do_scene_select(self) -> None:
        scene = self._selected_scene()
        if not scene or not self.app.ctrl:
            return
        self.app.preview_scene(scene)
        self.load_items(scene)

    def _selected_scene(self) -> str | None:
        sel = self.scene_list.curselection()
        if not sel:
            return None
        return self.scene_list.get(sel[0])

    def _switch_scene(self) -> None:
        scene = self._selected_scene()
        if not scene:
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self.app.log(f"切换场景 → {scene}", "INFO")
        run_in_thread(
            self.root,
            lambda: ctrl.set_current_scene(scene),
            lambda _: self.app.status_bar.set_scene(scene),
        )

    def _create_scene(self) -> None:
        name = simpledialog.askstring("新建场景", "请输入场景名称：", parent=self.root)
        if not name:
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self.app.log(f"创建场景: {name}", "SUCCESS")
        run_in_thread(
            self.root,
            lambda: ctrl.create_scene(name),
            lambda _: self.refresh(),
        )

    def _delete_scene(self) -> None:
        scene = self._selected_scene()
        if not scene:
            return
        if not messagebox.askyesno("删除场景", f"确认删除场景「{scene}」？"):
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self.app.log(f"删除场景: {scene}", "WARNING")
        run_in_thread(
            self.root,
            lambda: ctrl.remove_scene(scene),
            lambda _: self.refresh(),
        )

    def _rename_scene(self) -> None:
        scene = self._selected_scene()
        if not scene:
            return
        new_name = simpledialog.askstring(
            "重命名场景", f"请输入「{scene}」的新名称：",
            initialvalue=scene, parent=self.root
        )
        if not new_name or new_name == scene:
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        self.app.log(f"重命名场景: {scene} → {new_name}", "INFO")
        run_in_thread(
            self.root,
            lambda: ctrl.req.set_scene_name(
                scene_name=scene, new_scene_name=new_name
            ),
            lambda _: self.refresh(),
        )

    def _show_context_menu(self, event) -> None:
        idx = self.scene_list.nearest(event.y)
        self.scene_list.selection_set(idx)
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _toggle_item(self) -> None:
        sel = self.item_tree.selection()
        if not sel:
            return
        item_id = int(sel[0])
        scene = self._selected_scene() or ""
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        # 读当前状态并反转
        vals = self.item_tree.item(sel[0], "values")
        new_enabled = (vals[2] != "✓")
        run_in_thread(
            self.root,
            lambda: ctrl.set_scene_item_enabled(scene, item_id, new_enabled),
            lambda _: self.load_items(scene),
        )

    def _delete_item(self) -> None:
        sel = self.item_tree.selection()
        if not sel:
            return
        item_id = int(sel[0])
        scene = self._selected_scene() or ""
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            self.root,
            lambda: ctrl.remove_scene_item(scene, item_id),
            lambda _: self.load_items(scene),
        )
