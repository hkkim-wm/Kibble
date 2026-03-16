from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QMenu, QWidget, QVBoxLayout,
    QRadioButton, QHBoxLayout, QButtonGroup, QComboBox, QApplication,
)

from ui.i18n import I18n


class ResultsTableModel(QAbstractTableModel):
    """Model for search results display."""

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._results: List[Dict[str, Any]] = []
        self._columns: List[str] = []

    def set_results(self, results: List[Dict[str, Any]], columns: List[str]) -> None:
        self.beginResetModel()
        self._results = results
        self._columns = columns
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._results = []
        self._columns = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._results)

    def columnCount(self, parent=QModelIndex()) -> int:
        if not self._columns:
            return 0
        return len(self._columns) + 1  # +1 for score column

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._results):
            return None
        if col == 0:
            return self._results[row].get("score", 0)
        col_name = self._columns[col - 1] if col - 1 < len(self._columns) else ""
        return self._results[row].get(col_name, "")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return self._i18n.t("match_pct")
            if section - 1 < len(self._columns):
                return self._columns[section - 1]
        return None

    def get_row_data(self, row: int) -> Dict[str, Any]:
        if 0 <= row < len(self._results):
            return self._results[row]
        return {}

    def get_cell_text(self, row: int, col: int) -> str:
        index = self.index(row, col)
        val = self.data(index)
        return str(val) if val is not None else ""


class ResultsTableView(QWidget):
    """Widget containing view mode toggle + QTableView for results."""

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._model: Optional[ResultsTableModel] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # View mode toggle row
        toggle_layout = QHBoxLayout()
        self._view_group = QButtonGroup(self)
        self._three_col_radio = QRadioButton(self._i18n.t("three_col_view"))
        self._source_target_radio = QRadioButton(self._i18n.t("source_target_view"))
        self._source_target_radio.setChecked(True)
        self._view_group.addButton(self._three_col_radio, 0)
        self._view_group.addButton(self._source_target_radio, 1)
        toggle_layout.addWidget(self._three_col_radio)

        # Target language dropdown (visible only in three-column mode)
        self._lang_combo = QComboBox()
        self._lang_combo.setVisible(False)
        toggle_layout.addWidget(self._lang_combo)

        toggle_layout.addStretch()
        toggle_layout.addWidget(self._source_target_radio)
        layout.addLayout(toggle_layout)

        # Table view
        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table.setSortingEnabled(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

        # Connect view mode toggle
        self._view_group.idToggled.connect(self._on_view_mode_changed)

    def set_model(self, model: ResultsTableModel):
        self._table.setModel(model)
        self._model = model

    def set_target_languages(self, languages: List[str]):
        self._lang_combo.clear()
        for lang in languages:
            self._lang_combo.addItem(lang)
        en_idx = next((i for i, l in enumerate(languages) if l.upper() in ("EN", "ENGLISH", "영어")), 0)
        if languages:
            self._lang_combo.setCurrentIndex(en_idx)

    def _on_view_mode_changed(self, button_id: int, checked: bool):
        if not checked:
            return
        self._lang_combo.setVisible(button_id == 0)

    def _on_double_click(self, index: QModelIndex):
        if self._model:
            text = self._model.get_cell_text(index.row(), index.column())
            if text:
                QApplication.clipboard().setText(text)

    def _show_context_menu(self, position):
        if not self._model:
            return
        index = self._table.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        row_data = self._model.get_row_data(index.row())

        copy_row_action = QAction(self._i18n.t("copy_row"), self)
        copy_row_action.triggered.connect(lambda: self._copy_rows())
        menu.addAction(copy_row_action)

        copy_cell_action = QAction(self._i18n.t("copy_cell"), self)
        cell_text = self._model.get_cell_text(index.row(), index.column())
        copy_cell_action.triggered.connect(lambda: QApplication.clipboard().setText(cell_text))
        menu.addAction(copy_cell_action)

        menu.addSeparator()

        copy_source_action = QAction(self._i18n.t("copy_source_only"), self)
        source_text = row_data.get("source", "")
        copy_source_action.triggered.connect(lambda: QApplication.clipboard().setText(source_text))
        menu.addAction(copy_source_action)

        copy_target_action = QAction(self._i18n.t("copy_target_only"), self)
        target_text = row_data.get("target", "")
        copy_target_action.triggered.connect(lambda: QApplication.clipboard().setText(target_text))
        menu.addAction(copy_target_action)

        menu.exec(self._table.viewport().mapToGlobal(position))

    def _copy_rows(self):
        if not self._model:
            return
        selection = self._table.selectionModel()
        if not selection.hasSelection():
            return
        rows = sorted(set(idx.row() for idx in selection.selectedIndexes()))
        lines = []
        for row in rows:
            cols = []
            for col in range(self._model.columnCount()):
                cols.append(self._model.get_cell_text(row, col))
            lines.append("\t".join(cols))
        QApplication.clipboard().setText("\n".join(lines))

    def copy_selected(self):
        self._copy_rows()

    def get_view_mode(self) -> str:
        return "three_column" if self._three_col_radio.isChecked() else "source_target"

    def set_view_mode(self, mode: str):
        if mode == "three_column":
            self._three_col_radio.setChecked(True)
        else:
            self._source_target_radio.setChecked(True)

    def update_translations(self):
        self._three_col_radio.setText(self._i18n.t("three_col_view"))
        self._source_target_radio.setText(self._i18n.t("source_target_view"))
