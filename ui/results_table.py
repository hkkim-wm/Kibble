import re
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QAction, QTextDocument, QPalette, QAbstractTextDocumentLayout
from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QMenu, QWidget, QVBoxLayout,
    QRadioButton, QHBoxLayout, QButtonGroup, QComboBox, QApplication,
    QCheckBox, QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)

from ui.i18n import I18n


class HighlightDelegate(QStyledItemDelegate):
    """Delegate that highlights search terms in cells.

    Supports two highlight queries:
    - search_query: highlighted in the searched column (yellow)
    - filter_query: highlighted in the filtered columns (light blue)
    Both are highlighted in all non-meta columns for maximum visibility.
    """

    # Light tint for target cells that are translation pairs of matched source
    TARGET_TINT = "#FFF9C4"  # Very light yellow

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_query = ""
        self._filter_query = ""
        self._highlight_columns: set = set()  # All non-meta column indices
        self._source_columns: set = set()     # Source column indices
        self._target_columns: set = set()     # Target column indices

    def set_queries(self, search_query: str = "", filter_query: str = ""):
        self._search_query = search_query
        self._filter_query = filter_query

    def set_highlight_columns(self, columns: set, source_columns: set = None, target_columns: set = None):
        self._highlight_columns = columns
        self._source_columns = source_columns or set()
        self._target_columns = target_columns or set()

    def _has_highlights(self) -> bool:
        return bool(self._search_query or self._filter_query)

    def _make_highlighted_html(self, text: str) -> str:
        """Insert highlight tags around matched terms in text."""
        if not text:
            return text
        # Escape HTML entities
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # Apply search query highlight (yellow)
        if self._search_query:
            pattern = re.compile(re.escape(self._search_query), re.IGNORECASE)
            escaped = pattern.sub(
                lambda m: f'<span style="background-color:#FFEB3B;padding:0 1px">{m.group()}</span>',
                escaped,
            )
        # Apply filter query highlight (light blue)
        if self._filter_query:
            pattern = re.compile(re.escape(self._filter_query), re.IGNORECASE)
            escaped = pattern.sub(
                lambda m: f'<span style="background-color:#81D4FA;padding:0 1px">{m.group()}</span>',
                escaped,
            )
        return escaped

    def paint(self, painter, option, index):
        if not self._has_highlights() or index.column() not in self._highlight_columns:
            super().paint(painter, option, index)
            return

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return

        text_str = str(text)
        text_lower = text_str.lower()
        col = index.column()

        # Check if any query literally matches this cell text
        has_substring_match = False
        if self._search_query and self._search_query.lower() in text_lower:
            has_substring_match = True
        if self._filter_query and self._filter_query.lower() in text_lower:
            has_substring_match = True

        # Target columns always get a tint when search is active (they are translation pairs)
        is_target_cell = col in self._target_columns and self._search_query

        if not has_substring_match and not is_target_cell:
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        painter.save()

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif is_target_cell and not has_substring_match:
            # Light tint for target cells without literal match
            from PyQt6.QtGui import QColor
            painter.fillRect(option.rect, QColor(self.TARGET_TINT))
        else:
            painter.fillRect(option.rect, option.palette.base())

        doc = QTextDocument()
        if has_substring_match:
            html = self._make_highlighted_html(text_str)
        else:
            # No substring match but target tint — show plain text
            html = text_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        doc.setHtml(html)
        doc.setDefaultFont(option.font)
        doc.setTextWidth(option.rect.width())

        painter.translate(option.rect.topLeft())
        doc.drawContents(painter, QRectF(0, 0, option.rect.width(), option.rect.height()))

        painter.restore()


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
        return len(self._columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._results) or col >= len(self._columns):
            return None
        col_name = self._columns[col]
        return self._results[row].get(col_name, "")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section < len(self._columns):
                return self._columns[section]
        return None

    def get_columns(self) -> List[str]:
        return list(self._columns)

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

    view_mode_changed = pyqtSignal(str)  # "three_column" or "source_target"

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

        # Word wrap checkbox
        self._wrap_cb = QCheckBox(self._i18n.t("word_wrap"))
        self._wrap_cb.toggled.connect(self._on_wrap_toggled)
        toggle_layout.addWidget(self._wrap_cb)

        layout.addLayout(toggle_layout)

        # Table view
        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table.setSortingEnabled(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.setWordWrap(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setDefaultSectionSize(200)

        # Highlight delegate
        self._highlight_delegate = HighlightDelegate(self._table)
        self._table.setItemDelegate(self._highlight_delegate)

        layout.addWidget(self._table)

        # Connect view mode toggle and language selector
        self._view_group.idToggled.connect(self._on_view_mode_changed)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)

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

    def set_highlight_queries(self, search_query: str = "", filter_query: str = "",
                              search_direction: str = "source"):
        """Set highlight queries for source and target columns."""
        self._highlight_delegate.set_queries(
            search_query=search_query,
            filter_query=filter_query,
        )
        if self._model:
            columns = self._model.get_columns()
            meta_name = self._i18n.t("meta_info")
            source_name = self._i18n.t("source_col")
            all_cols = {i for i, c in enumerate(columns) if c != meta_name}
            source_cols = {i for i, c in enumerate(columns) if c == source_name}
            target_cols = {i for i, c in enumerate(columns) if c != meta_name and c != source_name}
            self._highlight_delegate.set_highlight_columns(
                all_cols, source_columns=source_cols, target_columns=target_cols
            )
        self._table.viewport().update()

    def _on_view_mode_changed(self, button_id: int, checked: bool):
        if not checked:
            return
        self._lang_combo.setVisible(button_id == 0)
        mode = "three_column" if button_id == 0 else "source_target"
        self.view_mode_changed.emit(mode)

    def _on_wrap_toggled(self, checked: bool):
        self._table.setWordWrap(checked)
        if checked:
            self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        else:
            self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            self._table.verticalHeader().setDefaultSectionSize(30)

    def _on_lang_changed(self, index: int):
        if self._three_col_radio.isChecked():
            self.view_mode_changed.emit("three_column")

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

    def get_selected_target_language(self) -> str:
        return self._lang_combo.currentText() if self._lang_combo.currentText() else ""

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
        self._wrap_cb.setText(self._i18n.t("word_wrap"))
