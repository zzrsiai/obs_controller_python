"""
gui/tab_filter.py  ——  滤镜管理标签页（PyQt5 版）
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)
from PyQt5.QtCore import Qt

from .utils import run_in_thread, FONT_BOLD

if TYPE_CHECKING:
    from .app import OBSGui


# 内置预设名称
PRESET_NAMES = [
    "美颜-轻度", "美颜-中度", "美颜-强度",
    "HDR感", "电影感", "夜间模式",
    "复古胶片", "高对比黑白",
]


class FilterTab(QWidget):
    """滤镜管理：选择输入源 → 查看/启用/禁用/删除该源的滤镜 + 预设快速应用。"""

    def __init__(self, parent, app: "OBSGui"):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 顶部：输入源选择
        top = QHBoxLayout()
        top.addWidget(QLabel("输入源:"))
        self._src_cb = QComboBox()
        self._src_cb.setFixedWidth(240)
        self._src_cb.currentIndexChanged.connect(self._load_filters)
        top.addWidget(self._src_cb)
        btn_refresh_src = QPushButton("🔄")
        btn_refresh_src.setProperty("outline", True)
        btn_refresh_src.clicked.connect(self._load_sources)
        top.addWidget(btn_refresh_src)
        top.addStretch()
        layout.addLayout(top)

        # 滤镜表格
        layout.addWidget(QLabel("该源的滤镜列表"))

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["滤镜名称", "类型", "启用"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._table)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_toggle = QPushButton("启用/禁用")
        btn_toggle.setProperty("warning", True)
        btn_toggle.clicked.connect(self._toggle_filter)
        btn_row.addWidget(btn_toggle)

        btn_delete = QPushButton("删除滤镜")
        btn_delete.setProperty("danger", True)
        btn_delete.clicked.connect(self._delete_filter)
        btn_row.addWidget(btn_delete)

        btn_row.addStretch()

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setProperty("outline", True)
        btn_refresh.clicked.connect(self._load_filters)
        btn_row.addWidget(btn_refresh)
        layout.addLayout(btn_row)

        # 预设快速应用
        layout.addWidget(QLabel("预设快速应用"))
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设名称:"))
        self._preset_cb = QComboBox()
        self._preset_cb.addItems(PRESET_NAMES)
        self._preset_cb.setFixedWidth(180)
        preset_row.addWidget(self._preset_cb)

        btn_apply = QPushButton("应用预设")
        btn_apply.clicked.connect(self._apply_preset)
        preset_row.addWidget(btn_apply)
        preset_row.addStretch()
        layout.addLayout(preset_row)

    # ── 加载输入源列表 ────────────────────────────────────────

    def _load_sources(self) -> None:
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(ctrl.get_input_list, self._on_sources)

    def _on_sources(self, inputs: list) -> None:
        names = []
        for inp in inputs:
            n = inp if isinstance(inp, str) else inp.get("name", "")
            if n:
                names.append(n)
        self._src_cb.blockSignals(True)
        self._src_cb.clear()
        self._src_cb.addItems(names)
        self._src_cb.blockSignals(False)
        if names:
            self._load_filters()

    # ── 加载滤镜列表 ──────────────────────────────────────────

    def _load_filters(self) -> None:
        src = self._src_cb.currentText()
        if not src:
            return
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        run_in_thread(
            lambda: ctrl.get_filter_list(src),
            self._on_filters,
        )

    def _on_filters(self, filters) -> None:
        self._table.setRowCount(0)
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
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(name))
            self._table.setItem(row, 1, QTableWidgetItem(kind))
            self._table.setItem(row, 2, QTableWidgetItem(enabled))

    # ── 启用/禁用 ─────────────────────────────────────────────

    def _toggle_filter(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        filter_name = self._table.item(row, 0).text()
        src = self._src_cb.currentText()
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        enabled_item = self._table.item(row, 2)
        new_enabled = (enabled_item.text() != "✓")
        run_in_thread(
            lambda: ctrl.set_filter_enabled(src, filter_name, new_enabled),
            lambda _: self._load_filters(),
        )

    # ── 删除滤镜 ──────────────────────────────────────────────

    def _delete_filter(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        filter_name = self._table.item(row, 0).text()
        src = self._src_cb.currentText()
        ctrl = self.app.ctrl
        if ctrl is None:
            return
        reply = QMessageBox.question(
            self, "删除滤镜", f"确认删除滤镜「{filter_name}」？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        run_in_thread(
            lambda: ctrl.remove_filter(src, filter_name),
            lambda _: self._load_filters(),
        )

    # ── 预设应用 ──────────────────────────────────────────────

    def _apply_preset(self) -> None:
        src = self._src_cb.currentText()
        preset = self._preset_cb.currentText()
        ctrl = self.app.ctrl
        if ctrl is None or not src or not preset:
            return
        run_in_thread(
            lambda: ctrl.apply_filter_preset(src, preset),
            lambda _: self._load_filters(),
        )

    def refresh(self) -> None:
        self._load_sources()
