import re
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QSize, QRectF,
    QSortFilterProxyModel,
)
from PyQt6.QtGui import QAction, QFont, QTextDocument, QPalette, QAbstractTextDocumentLayout
from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QMenu, QWidget, QVBoxLayout, QLabel,
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

    def _get_conflict_bg(self, index) -> 'QColor | None':
        """Check if this cell is a conflicting translation cell via model BackgroundRole."""
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg is not None:
            from PyQt6.QtGui import QColor
            return QColor(bg) if not isinstance(bg, QColor) else bg
        return None

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

        # Check for conflict highlight (takes priority over target tint)
        conflict_bg = self._get_conflict_bg(index)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif conflict_bg is not None:
            painter.fillRect(option.rect, conflict_bg)
        elif is_target_cell and not has_substring_match:
            # Light tint for target cells without literal match
            from PyQt6.QtGui import QColor
            painter.fillRect(option.rect, QColor(self.TARGET_TINT))
        else:
            painter.fillRect(option.rect, option.palette.base())

        doc = QTextDocument()
        # Use palette text color so dark mode renders readable text
        text_color = option.palette.text().color().name()
        if has_substring_match:
            html = self._make_highlighted_html(text_str)
        else:
            html = text_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        doc.setHtml(f'<span style="color:{text_color}">{html}</span>')
        doc.setDefaultFont(option.font)
        doc.setTextWidth(option.rect.width())

        painter.translate(option.rect.topLeft())
        doc.drawContents(painter, QRectF(0, 0, option.rect.width(), option.rect.height()))

        painter.restore()


class ResultsTableModel(QAbstractTableModel):
    """Model for search results display. First column is always '%' (match score)."""

    SCORE_COL = "%"

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._results: List[Dict[str, Any]] = []
        self._columns: List[str] = []  # Does NOT include the score column

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

    # Custom roles
    DuplicateRole = Qt.ItemDataRole.UserRole + 1
    DupLangsRole = Qt.ItemDataRole.UserRole + 2

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._results):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                score = self._results[row].get("_score", "")
                is_dup = self._results[row].get("_is_dup", False)
                return f"⚠{score}" if is_dup else score
            col_name = self._columns[col - 1] if col - 1 < len(self._columns) else ""
            return self._results[row].get(col_name, "")

        # For sorting: return numeric score for column 0
        if role == Qt.ItemDataRole.UserRole:
            if col == 0:
                return self._results[row].get("_score_num", 0)
            col_name = self._columns[col - 1] if col - 1 < len(self._columns) else ""
            return self._results[row].get(col_name, "")

        # Duplicate flag
        if role == self.DuplicateRole:
            return self._results[row].get("_is_dup", False)

        # Background color: only highlight the specific language cells with conflicts
        if role == Qt.ItemDataRole.BackgroundRole:
            dup_langs = self._results[row].get("_dup_langs", set())
            if dup_langs and col > 0:
                col_name = self._columns[col - 1] if col - 1 < len(self._columns) else ""
                if col_name in dup_langs:
                    from PyQt6.QtGui import QColor
                    return QColor("#FFCCBC")  # Light orange/red tint

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return self.SCORE_COL
            if section - 1 < len(self._columns):
                return self._columns[section - 1]
        return None

    def get_columns(self) -> List[str]:
        """Return display columns (excluding score)."""
        return list(self._columns)

    def get_all_columns(self) -> List[str]:
        """Return all columns including score."""
        return [self.SCORE_COL] + list(self._columns)

    def get_row_data(self, row: int) -> Dict[str, Any]:
        if 0 <= row < len(self._results):
            return self._results[row]
        return {}

    def get_cell_text(self, row: int, col: int) -> str:
        index = self.index(row, col)
        val = self.data(index)
        return str(val) if val is not None else ""


class SortProxyModel(QSortFilterProxyModel):
    """Proxy model that sorts by UserRole for numeric columns."""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_data = self.sourceModel().data(left, Qt.ItemDataRole.UserRole)
        right_data = self.sourceModel().data(right, Qt.ItemDataRole.UserRole)
        # Numeric comparison for score column
        if isinstance(left_data, (int, float)) and isinstance(right_data, (int, float)):
            return left_data < right_data
        # String comparison for text columns
        return str(left_data or "").lower() < str(right_data or "").lower()


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

        # Font size control
        self._font_size_label = QLabel(self._i18n.t("font_size") + ":")
        toggle_layout.addWidget(self._font_size_label)
        self._font_size_combo = QComboBox()
        self._font_size_combo.addItems(["S", "M", "L", "XL"])
        self._font_size_map = {"S": 10, "M": 12, "L": 14, "XL": 16}
        self._font_size_combo.setCurrentIndex(1)  # Default: M (12)
        self._font_size_combo.setFixedWidth(55)
        self._font_size_combo.currentTextChanged.connect(self._on_font_size_changed)
        toggle_layout.addWidget(self._font_size_combo)
        self._current_font_size = 12

        layout.addLayout(toggle_layout)

        # Table view
        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self._table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.setWordWrap(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setDefaultSectionSize(200)
        # Make row heights adjustable by dragging
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.verticalHeader().setDefaultSectionSize(30)
        # Make % column narrow
        self._table.horizontalHeader().setMinimumSectionSize(35)

        # Highlight delegate
        self._highlight_delegate = HighlightDelegate(self._table)
        self._table.setItemDelegate(self._highlight_delegate)

        layout.addWidget(self._table)

        # Connect view mode toggle and language selector
        self._view_group.idToggled.connect(self._on_view_mode_changed)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)

    def set_model(self, model: ResultsTableModel):
        self._model = model
        self._proxy = SortProxyModel(self)
        self._proxy.setSourceModel(model)
        self._table.setModel(self._proxy)

    def set_target_languages(self, languages: List[str]):
        self._lang_combo.clear()
        for lang in languages:
            self._lang_combo.addItem(lang)
        en_idx = next((i for i, l in enumerate(languages) if l.upper() in ("EN", "ENGLISH", "영어")), 0)
        if languages:
            self._lang_combo.setCurrentIndex(en_idx)

    def resize_score_column(self):
        """Make the % column narrow."""
        if self._model and self._model.columnCount() > 0:
            self._table.setColumnWidth(0, 50)

    def set_highlight_queries(self, search_query: str = "", filter_query: str = "",
                              search_direction: str = "source"):
        """Set highlight queries for source and target columns."""
        self._highlight_delegate.set_queries(
            search_query=search_query,
            filter_query=filter_query,
        )
        if self._model:
            columns = self._model.get_columns()  # Excludes score column
            meta_name = self._i18n.t("meta_info")
            source_name = self._i18n.t("source_col")
            # +1 offset because column 0 is the score column
            all_cols = {i + 1 for i, c in enumerate(columns) if c != meta_name}
            source_cols = {i + 1 for i, c in enumerate(columns) if c == source_name}
            target_cols = {i + 1 for i, c in enumerate(columns) if c != meta_name and c != source_name}
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

    def _on_font_size_changed(self, size_label: str):
        size = self._font_size_map.get(size_label, 12)
        self._current_font_size = size
        font = self._table.font()
        font.setPointSize(size)
        self._table.setFont(font)
        self._table.viewport().update()

    def get_font_size(self) -> int:
        return self._current_font_size

    def set_font_size(self, size: int):
        self._current_font_size = size
        # Find matching label
        reverse_map = {v: k for k, v in self._font_size_map.items()}
        label = reverse_map.get(size, "M")
        self._font_size_combo.setCurrentText(label)
        font = self._table.font()
        font.setPointSize(size)
        self._table.setFont(font)

    def _on_wrap_toggled(self, checked: bool):
        self._table.setWordWrap(checked)
        if checked:
            self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        else:
            self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self._table.verticalHeader().setDefaultSectionSize(30)

    def _on_lang_changed(self, index: int):
        if self._three_col_radio.isChecked():
            self.view_mode_changed.emit("three_column")

    def _on_double_click(self, index: QModelIndex):
        """Copy clicked cell to clipboard."""
        if self._model and self._proxy:
            source_index = self._proxy.mapToSource(index)
            text = self._model.get_cell_text(source_index.row(), source_index.column())
            if text:
                QApplication.clipboard().setText(text)

    def _show_context_menu(self, position):
        if not self._model or not self._proxy:
            return
        proxy_index = self._table.indexAt(position)
        if not proxy_index.isValid():
            return
        source_index = self._proxy.mapToSource(proxy_index)

        menu = QMenu(self)
        row_data = self._model.get_row_data(source_index.row())

        copy_row_action = QAction(self._i18n.t("copy_row"), self)
        copy_row_action.triggered.connect(lambda: self._copy_rows())
        menu.addAction(copy_row_action)

        copy_cell_action = QAction(self._i18n.t("copy_cell"), self)
        cell_text = self._model.get_cell_text(source_index.row(), source_index.column())
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
        if not self._model or not self._proxy:
            return
        selection = self._table.selectionModel()
        if not selection.hasSelection():
            return
        proxy_rows = sorted(set(idx.row() for idx in selection.selectedIndexes()))
        lines = []
        for proxy_row in proxy_rows:
            cols = []
            for col in range(self._model.columnCount()):
                proxy_idx = self._proxy.index(proxy_row, col)
                source_idx = self._proxy.mapToSource(proxy_idx)
                cols.append(self._model.get_cell_text(source_idx.row(), source_idx.column()))
            lines.append("\t".join(cols))
        QApplication.clipboard().setText("\n".join(lines))

    def copy_selected(self):
        """Copy current cell text to clipboard (Ctrl+C)."""
        if not self._model or not self._proxy:
            return
        proxy_index = self._table.currentIndex()
        if proxy_index.isValid():
            source_index = self._proxy.mapToSource(proxy_index)
            text = self._model.get_cell_text(source_index.row(), source_index.column())
            if text:
                QApplication.clipboard().setText(text)

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
        self._font_size_label.setText(self._i18n.t("font_size") + ":")
