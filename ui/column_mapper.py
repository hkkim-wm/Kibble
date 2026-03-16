from typing import List, Tuple, Optional

import pandas as pd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QDialogButtonBox,
    QGroupBox,
)

from ui.i18n import I18n


class ColumnMapperDialog(QDialog):
    """Dialog for manually assigning source and target columns."""

    def __init__(self, df: pd.DataFrame, i18n: I18n,
                 current_source: str = "", current_targets: List[str] = None,
                 parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._df = df
        self._columns = list(df.columns)
        self._result_source: Optional[str] = current_source
        self._result_targets: List[str] = current_targets or []
        self.setWindowTitle(i18n.t("configure_columns"))
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Source column selector
        source_group = QGroupBox("Source Column")
        source_layout = QHBoxLayout(source_group)
        self._source_combo = QComboBox()
        for col in self._columns:
            self._source_combo.addItem(str(col))
        if self._result_source in self._columns:
            self._source_combo.setCurrentText(self._result_source)
        source_layout.addWidget(self._source_combo)
        layout.addWidget(source_group)

        # Target columns checkboxes
        target_group = QGroupBox("Target Columns")
        target_layout = QVBoxLayout(target_group)
        self._target_checks: dict[str, QCheckBox] = {}
        for col in self._columns:
            cb = QCheckBox(str(col))
            cb.setChecked(col in self._result_targets or col != self._result_source)
            self._target_checks[col] = cb
            target_layout.addWidget(cb)
        layout.addWidget(target_group)

        # Preview table (first 5 rows)
        preview_group = QGroupBox("Preview (first 5 rows)")
        preview_layout = QVBoxLayout(preview_group)
        preview_rows = min(5, len(self._df))
        self._preview = QTableWidget(preview_rows, len(self._columns))
        self._preview.setHorizontalHeaderLabels([str(c) for c in self._columns])
        for r in range(preview_rows):
            for c, col in enumerate(self._columns):
                val = str(self._df.iloc[r][col]) if pd.notna(self._df.iloc[r][col]) else ""
                self._preview.setItem(r, c, QTableWidgetItem(val))
        self._preview.resizeColumnsToContents()
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_group)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_combo.currentTextChanged.connect(self._on_source_changed)

    def _on_source_changed(self, source: str):
        for col, cb in self._target_checks.items():
            if col == source:
                cb.setChecked(False)
                cb.setEnabled(False)
            else:
                cb.setEnabled(True)

    def get_mapping(self) -> Tuple[str, List[str]]:
        source = self._source_combo.currentText()
        targets = [
            col for col, cb in self._target_checks.items()
            if cb.isChecked() and col != source
        ]
        return source, targets
