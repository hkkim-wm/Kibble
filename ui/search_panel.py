from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QRadioButton, QButtonGroup, QComboBox, QSlider,
    QLabel, QSpinBox,
)

from ui.i18n import I18n


class SearchPanel(QWidget):
    """Search controls panel: search box, options, filter, threshold."""

    search_requested = pyqtSignal(dict)

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._emit_search)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Row 1: Search box + button
        row1 = QHBoxLayout()
        self._search_label = QLabel(self._i18n.t("search_for"))
        row1.addWidget(self._search_label)
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(self._i18n.t("btn_search") + "...")
        self._search_box.textChanged.connect(self._on_text_changed)
        self._search_box.returnPressed.connect(self._on_search_clicked)
        row1.addWidget(self._search_box, stretch=1)
        self._search_btn = QPushButton(self._i18n.t("btn_search"))
        self._search_btn.clicked.connect(self._on_search_clicked)
        row1.addWidget(self._search_btn)
        main_layout.addLayout(row1)

        # Row 2: Checkboxes
        row2 = QHBoxLayout()
        self._case_cb = QCheckBox(self._i18n.t("case_sensitive"))
        row2.addWidget(self._case_cb)
        self._wildcard_cb = QCheckBox(self._i18n.t("add_wildcards"))
        row2.addWidget(self._wildcard_cb)
        row2.addStretch()
        main_layout.addLayout(row2)

        # Row 3: Radio buttons + match mode + threshold
        row3 = QHBoxLayout()
        self._direction_group = QButtonGroup(self)
        self._source_radio = QRadioButton(self._i18n.t("search_in_source"))
        self._source_radio.setChecked(True)
        self._target_radio = QRadioButton(self._i18n.t("search_in_target"))
        self._direction_group.addButton(self._source_radio, 0)
        self._direction_group.addButton(self._target_radio, 1)
        self._source_radio.toggled.connect(self._on_direction_changed)
        row3.addWidget(self._source_radio)
        row3.addWidget(self._target_radio)
        row3.addStretch()

        self._mode_label = QLabel(self._i18n.t("match_mode") + ":")
        row3.addWidget(self._mode_label)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            self._i18n.t("mode_both"),
            self._i18n.t("mode_substring"),
            self._i18n.t("mode_fuzzy"),
        ])
        row3.addWidget(self._mode_combo)

        self._threshold_label = QLabel(self._i18n.t("threshold") + ":")
        row3.addWidget(self._threshold_label)
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(0, 100)
        self._threshold_slider.setValue(50)
        self._threshold_slider.setFixedWidth(120)
        row3.addWidget(self._threshold_slider)
        self._threshold_value = QLabel("50%")
        self._threshold_slider.valueChanged.connect(
            lambda v: self._threshold_value.setText(f"{v}%")
        )
        row3.addWidget(self._threshold_value)
        main_layout.addLayout(row3)

        # Row 4: Filter + limit + total hits
        row4 = QHBoxLayout()
        self._filter_label = QLabel(self._i18n.t("filter_target"))
        row4.addWidget(self._filter_label)
        self._filter_box = QLineEdit()
        row4.addWidget(self._filter_box, stretch=1)

        self._limit_label = QLabel(self._i18n.t("limit") + ":")
        row4.addWidget(self._limit_label)
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(10, 1000)
        self._limit_spin.setValue(200)
        self._limit_spin.setSingleStep(10)
        row4.addWidget(self._limit_spin)

        self._hits_label = QLabel(self._i18n.t("total_hits") + ": 0")
        row4.addWidget(self._hits_label)
        main_layout.addLayout(row4)

    def _on_text_changed(self, text: str):
        self._debounce_timer.stop()
        if len(text) >= 2:
            self._debounce_timer.start()

    def _on_search_clicked(self):
        self._debounce_timer.stop()
        self._emit_search()

    def _on_direction_changed(self):
        if self._source_radio.isChecked():
            self._filter_label.setText(self._i18n.t("filter_target"))
        else:
            self._filter_label.setText(self._i18n.t("filter_source"))

    def _get_mode_value(self) -> str:
        idx = self._mode_combo.currentIndex()
        return ["both", "substring", "fuzzy"][idx]

    def _emit_search(self):
        query = self._search_box.text().strip()
        if len(query) < 2:
            return
        self.search_requested.emit({
            "query": query,
            "mode": self._get_mode_value(),
            "threshold": self._threshold_slider.value(),
            "limit": self._limit_spin.value(),
            "case_sensitive": self._case_cb.isChecked(),
            "wildcards": self._wildcard_cb.isChecked(),
            "direction": "source" if self._source_radio.isChecked() else "target",
            "filter_text": self._filter_box.text().strip(),
        })

    def set_total_hits(self, count: int):
        self._hits_label.setText(f"{self._i18n.t('total_hits')}: {count}")

    def focus_search(self):
        self._search_box.setFocus()
        self._search_box.selectAll()

    def clear_search(self):
        self._search_box.clear()

    def get_config(self) -> dict:
        return {
            "last_search": self._search_box.text(),
            "match_mode": self._get_mode_value(),
            "threshold": self._threshold_slider.value(),
            "search_direction": "source" if self._source_radio.isChecked() else "target",
            "case_sensitive": self._case_cb.isChecked(),
            "limit": self._limit_spin.value(),
        }

    def restore_config(self, config: dict):
        self._search_box.setText(config.get("last_search", ""))
        mode = config.get("match_mode", "both")
        mode_idx = {"both": 0, "substring": 1, "fuzzy": 2}.get(mode, 0)
        self._mode_combo.setCurrentIndex(mode_idx)
        self._threshold_slider.setValue(config.get("threshold", 50))
        if config.get("search_direction", "source") == "target":
            self._target_radio.setChecked(True)
        else:
            self._source_radio.setChecked(True)
        self._case_cb.setChecked(config.get("case_sensitive", False))
        self._limit_spin.setValue(config.get("limit", 200))

    def update_translations(self):
        self._search_label.setText(self._i18n.t("search_for"))
        self._search_box.setPlaceholderText(self._i18n.t("btn_search") + "...")
        self._search_btn.setText(self._i18n.t("btn_search"))
        self._case_cb.setText(self._i18n.t("case_sensitive"))
        self._wildcard_cb.setText(self._i18n.t("add_wildcards"))
        self._source_radio.setText(self._i18n.t("search_in_source"))
        self._target_radio.setText(self._i18n.t("search_in_target"))
        self._mode_label.setText(self._i18n.t("match_mode") + ":")
        self._mode_combo.setItemText(0, self._i18n.t("mode_both"))
        self._mode_combo.setItemText(1, self._i18n.t("mode_substring"))
        self._mode_combo.setItemText(2, self._i18n.t("mode_fuzzy"))
        self._threshold_label.setText(self._i18n.t("threshold") + ":")
        self._on_direction_changed()
        self._limit_label.setText(self._i18n.t("limit") + ":")
