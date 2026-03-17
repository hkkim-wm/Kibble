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
    """Delegate that highlights search query matches with yellow background in cells."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""
        self._highlight_columns: set = set()  # Column indices to highlight

    def set_query(self, query: str):
        self._query = query

    def set_highlight_columns(self, columns: set):
        self._highlight_columns = columns

    def _make_highlighted_html(self, text: str) -> str:
        """Insert <mark> tags around query matches in text."""
        if not self._query or not text:
            return text
        # Escape HTML entities in text first
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # Case-insensitive highlight
        pattern = re.compile(re.escape(self._query), re.IGNORECASE)
        highlighted = pattern.sub(
            lambda m: f'<mark style="background-color:#FFEB3B;padding:0 1px">{m.group()}</mark>',
            escaped,
        )
        return highlighted

    def paint(self, painter, option, index):
        if not self._query or index.column() not in self._highlight_columns:
            super().paint(painter, option, index)
            return

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        painter.save()

        # Draw background for selection
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # Render highlighted HTML
        doc = QTextDocument()
        html = self._make_highlighted_html(str(text))
        doc.setHtml(html)
        doc.setDefaultFont(option.font)
        doc.setTextWidth(option.rect.width())

        painter.translate(option.rect.topLeft())
        doc.drawContents(painter, QRectF(0, 0, option.rect.width(), option.rect.height()))

        painter.restore()

    def sizeHint(self, option, index):
        if not self._query or index.column() not in self._highlight_columns:
            return super().sizeHint(option, index)

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setHtml(self._make_highlighted_html(str(text)))
        doc.setDefaultFont(option.font)
        doc.setTextWidth(option.rect.width() if option.rect.width() > 0 else 200)
        return QSize(int(doc.idealWidth()), int(doc.size().height()))


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

    def set_highlight_query(self, query: str):
        """Set the search query for highlighting in source and target columns."""
        self._highlight_delegate.set_query(query)
        # Determine which columns to highlight (all except meta-info)
        if self._model:
            columns = self._model.get_columns()
            meta_name = self._i18n.t("meta_info")
            highlight_cols = {i for i, c in enumerate(columns) if c != meta_name}
            self._highlight_delegate.set_highlight_columns(highlight_cols)
        # Force repaint
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
