import os
import re
from typing import Dict, List, Any, Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog, QStatusBar,
    QLabel, QHBoxLayout, QPushButton, QMessageBox,
)

from core.parser import detect_columns, check_entry_limit
from core.search import SearchConfig
from core.session import SessionManager, DEFAULT_SESSION
from ui.i18n import I18n
from ui.search_panel import SearchPanel
from ui.file_tabs import FileTabs
from ui.results_table import ResultsTableModel, ResultsTableView
from ui.drop_zone import DropZoneFilter, ToastNotification
from ui.column_mapper import ColumnMapperDialog
from workers.parse_worker import ParseWorker
from workers.search_worker import SearchWorker

APP_VERSION = "1.0"
HANGUL_RE = re.compile(r"[\uAC00-\uD7AF]")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._i18n = I18n(language="ko")

        # Data storage
        self._loaded_files: Dict[str, pd.DataFrame] = {}
        self._column_mappings: Dict[str, dict] = {}
        self._total_entries = 0

        # Workers
        self._parse_workers: List[ParseWorker] = []
        self._search_worker: Optional[SearchWorker] = None
        self._current_search_entries: List[Dict[str, Any]] = []

        # Session
        exe_dir = os.path.dirname(os.path.abspath(__file__))
        fallback = os.path.join(os.environ.get("APPDATA", ""), "Kibble")
        self._session = SessionManager(primary_dir=exe_dir, fallback_dir=fallback)

        self._setup_ui()
        self._setup_shortcuts()
        self._try_restore_session()

    def _setup_ui(self):
        self.setWindowTitle("Kibble")
        self.resize(1200, 800)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Language toggle
        title_bar = QHBoxLayout()
        title_bar.addStretch()
        self._lang_btn = QPushButton("EN | 한국어")
        self._lang_btn.setFixedWidth(100)
        self._lang_btn.clicked.connect(self._toggle_language)
        title_bar.addWidget(self._lang_btn)
        layout.addLayout(title_bar)

        # Search panel
        self._search_panel = SearchPanel(self._i18n)
        self._search_panel.search_requested.connect(self._on_search_requested)
        layout.addWidget(self._search_panel)

        # File tabs
        self._file_tabs = FileTabs(self._i18n)
        self._file_tabs.tab_changed.connect(self._on_tab_changed)
        self._file_tabs.file_closed.connect(self._on_file_closed)
        self._file_tabs.configure_requested.connect(self._on_configure_columns)
        layout.addWidget(self._file_tabs)

        # Results table
        self._table_model = ResultsTableModel(self._i18n)
        self._results_view = ResultsTableView(self._i18n)
        self._results_view.set_model(self._table_model)
        self._results_view.view_mode_changed.connect(self._on_view_mode_changed)
        layout.addWidget(self._results_view, stretch=1)

        # Last search results cache for view mode switching
        self._last_search_results: list = []
        self._last_search_config: dict = {}

        # Toast notification
        self._toast = ToastNotification(central)

        # Drop zone filter
        self._drop_filter = DropZoneFilter(self._i18n)
        self._drop_filter.files_dropped.connect(self._on_files_dropped)
        self._drop_filter.invalid_files_dropped.connect(self._on_invalid_files_dropped)
        self.installEventFilter(self._drop_filter)

        # Status bar
        status_bar = QStatusBar()
        self._drop_hint = QLabel(f"\U0001F415 {self._i18n.t('drop_hint')}")
        status_bar.addWidget(self._drop_hint, stretch=1)
        self._status_info = QLabel(f"Kibble v{APP_VERSION}")
        status_bar.addPermanentWidget(self._status_info)
        self.setStatusBar(status_bar)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self._search_panel.focus_search)
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_file_dialog)
        QShortcut(QKeySequence("Ctrl+C"), self, self._results_view.copy_selected)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Escape"), self, self._search_panel.clear_search)

    def _toggle_language(self):
        new_lang = "en" if self._i18n.language == "ko" else "ko"
        self._i18n.set_language(new_lang)
        self._update_all_translations()

    def _update_all_translations(self):
        self._search_panel.update_translations()
        self._file_tabs.update_translations()
        self._results_view.update_translations()
        self._drop_hint.setText(f"\U0001F415 {self._i18n.t('drop_hint')}")

    # --- File loading ---

    def _open_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Files",
            "",
            "Terminology Files (*.xlsx *.csv *.txt);;All Files (*)",
        )
        if paths:
            self._load_files(paths)

    def _on_files_dropped(self, paths: list):
        self._load_files(paths)

    def _on_invalid_files_dropped(self, paths: list):
        self._toast.show_message(self._i18n.t("unsupported_format"))

    def _load_files(self, paths: list):
        for path in paths:
            if path in self._loaded_files:
                continue
            worker = ParseWorker(path)
            worker.finished.connect(self._on_file_parsed)
            worker.error.connect(self._on_parse_error)
            worker.extra_sheets.connect(self._on_extra_sheets)
            self._parse_workers.append(worker)
            worker.start()

    def _on_file_parsed(self, path: str, df: pd.DataFrame, source: str, targets: list):
        try:
            check_entry_limit(self._total_entries, len(df), os.path.basename(path))
        except ValueError as e:
            self._toast.show_message(str(e))
            return

        self._loaded_files[path] = df
        self._column_mappings[path] = {"source": source, "targets": targets}
        self._total_entries += len(df)

        display_name = os.path.basename(path)
        self._file_tabs.add_file_tab(path, display_name)
        self._update_status()

        # Update target language list in results view
        all_targets = set()
        for mapping in self._column_mappings.values():
            all_targets.update(mapping["targets"])
        self._results_view.set_target_languages(sorted(all_targets))

        # Auto-open column mapper if no Korean detected (low confidence)
        sample = " ".join(str(v) for v in df[source].head(5).dropna())
        if not HANGUL_RE.search(sample):
            dialog = ColumnMapperDialog(df, self._i18n, source, targets, parent=self)
            if dialog.exec():
                new_source, new_targets = dialog.get_mapping()
                self._column_mappings[path] = {"source": new_source, "targets": new_targets}

    def _on_parse_error(self, path: str, message: str):
        self._toast.show_message(message)

    def _on_extra_sheets(self, path: str, count: int):
        name = os.path.basename(path)
        self._toast.show_message(self._i18n.t("extra_sheets", file=name, n=count))

    def _on_file_closed(self, path: str):
        if path in self._loaded_files:
            self._total_entries -= len(self._loaded_files[path])
            del self._loaded_files[path]
            del self._column_mappings[path]
        self._file_tabs.remove_file_tab(path)
        self._update_status()

    def _close_current_tab(self):
        current = self._file_tabs.get_current_file()
        if current != "all":
            self._on_file_closed(current)

    # --- Column mapping ---

    def _on_configure_columns(self):
        current = self._file_tabs.get_current_file()
        if current == "all":
            files = self._file_tabs.get_loaded_files()
            if not files:
                return
            current = files[0]

        if current not in self._loaded_files:
            return

        df = self._loaded_files[current]
        mapping = self._column_mappings.get(current, {})
        dialog = ColumnMapperDialog(
            df, self._i18n,
            current_source=mapping.get("source", ""),
            current_targets=mapping.get("targets", []),
            parent=self,
        )
        if dialog.exec():
            source, targets = dialog.get_mapping()
            self._column_mappings[current] = {"source": source, "targets": targets}

    # --- Search ---

    def _on_search_requested(self, config: dict):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.cancel()
            self._search_worker.wait(500)

        entries = self._build_search_entries(
            config["direction"],
            self._file_tabs.get_current_file(),
        )

        search_config = SearchConfig(
            query=config["query"],
            mode=config["mode"],
            threshold=config["threshold"],
            limit=config["limit"],
            case_sensitive=config["case_sensitive"],
            wildcards=config["wildcards"],
        )

        self._current_search_entries = entries
        self._search_worker = SearchWorker(entries, search_config)
        self._search_worker.finished.connect(
            lambda results, count: self._on_search_finished(results, count, config)
        )
        self._search_worker.start()

    def _build_search_entries(self, direction: str, file_filter: str) -> list:
        entries = []
        files = (
            self._loaded_files.items()
            if file_filter == "all"
            else [(file_filter, self._loaded_files[file_filter])]
            if file_filter in self._loaded_files
            else []
        )

        for path, df in files:
            mapping = self._column_mappings.get(path, {})
            if direction == "source":
                search_col = mapping.get("source", df.columns[0])
            else:
                target_cols = mapping.get("targets", [df.columns[1] if len(df.columns) > 1 else df.columns[0]])
                search_col = target_cols[0] if target_cols else df.columns[0]

            for i in range(len(df)):
                text = str(df.iloc[i].get(search_col, "")) if search_col in df.columns else ""
                if not text or text == "nan":
                    continue
                entry = {
                    "text": text,
                    "index": len(entries),
                    "row_idx": i,
                    "file_path": path,
                    "source": str(df.iloc[i].get(mapping.get("source", df.columns[0]), "")),
                }
                for t_col in mapping.get("targets", []):
                    if t_col in df.columns:
                        entry[t_col] = str(df.iloc[i].get(t_col, ""))
                entries.append(entry)

        return entries

    def _on_search_finished(self, results: list, total_hits: int, config: dict):
        entries = self._current_search_entries
        self._search_panel.set_total_hits(total_hits)

        # Apply secondary filter
        filter_text = config.get("filter_text", "").strip().lower()
        if filter_text:
            direction = config.get("direction", "source")
            filtered = []
            for r in results:
                idx = r["index"]
                if idx < len(entries):
                    entry = entries[idx]
                    if direction == "source":
                        for key, val in entry.items():
                            if key not in ("text", "index", "row_idx", "file_path", "source") and filter_text in str(val).lower():
                                filtered.append(r)
                                break
                    else:
                        if filter_text in entry.get("source", "").lower():
                            filtered.append(r)
            results = filtered
            self._search_panel.set_total_hits(len(results))

        # Build table data (cached for view mode switching)
        table_data = []
        current_file = self._file_tabs.get_current_file()
        for r in results:
            idx = r["index"]
            if idx < len(entries):
                entry = entries[idx]
                row = {"score": r["score"], "source": entry.get("source", "")}
                mapping = self._column_mappings.get(entry["file_path"], {})
                for t_col in mapping.get("targets", []):
                    row[t_col] = entry.get(t_col, "")
                if current_file == "all":
                    row["meta"] = os.path.basename(entry.get("file_path", ""))
                table_data.append(row)

        self._last_table_data = table_data
        self._last_current_file = current_file
        self._render_table()

    def _render_table(self):
        """Render table data respecting current view mode."""
        table_data = getattr(self, "_last_table_data", [])
        current_file = getattr(self, "_last_current_file", "all")
        if not table_data:
            return

        view_mode = self._results_view.get_view_mode()
        all_targets = set()
        for mapping in self._column_mappings.values():
            all_targets.update(mapping["targets"])
        sorted_targets = sorted(all_targets)

        if view_mode == "three_column":
            # Show only one target language
            selected_lang = self._results_view.get_selected_target_language()
            if not selected_lang and sorted_targets:
                selected_lang = sorted_targets[0]
            visible_targets = [selected_lang] if selected_lang and selected_lang in all_targets else sorted_targets[:1]
        else:
            # Source + target: show all target columns
            visible_targets = sorted_targets

        columns = [self._i18n.t("source_col")]
        columns.extend(visible_targets)
        if current_file == "all":
            columns.append(self._i18n.t("meta_info"))

        display_data = []
        for row in table_data:
            d = {"score": row["score"], self._i18n.t("source_col"): row.get("source", "")}
            for t in visible_targets:
                d[t] = row.get(t, "")
            if current_file == "all":
                d[self._i18n.t("meta_info")] = row.get("meta", "")
            d["source"] = row.get("source", "")
            d["target"] = " | ".join(row.get(t, "") for t in visible_targets)
            display_data.append(d)

        self._table_model.set_results(display_data, columns)

    def _on_view_mode_changed(self, mode: str):
        """Re-render table when view mode toggle changes."""
        self._render_table()

    def _on_tab_changed(self, file_path: str):
        pass  # Search re-triggered by user

    # --- Status ---

    def _update_status(self):
        file_count = len(self._loaded_files)
        self._drop_hint.setText(
            f"\U0001F415 {self._i18n.t('drop_hint')}  |  "
            f"{file_count} files, {self._total_entries} entries"
        )

    # --- Session ---

    def _try_restore_session(self):
        session = self._session.load()
        if session.get("last_files"):
            reply = QMessageBox.question(
                self,
                "Kibble",
                self._i18n.t("restore_session"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._restore_session(session)
        size = session.get("window_size", [1200, 800])
        pos = session.get("window_position", [100, 100])
        self.resize(size[0], size[1])
        self.move(pos[0], pos[1])
        lang = session.get("ui_language", "ko")
        self._i18n.set_language(lang)
        self._update_all_translations()

    def _restore_session(self, session: dict):
        self._search_panel.restore_config(session)
        self._column_mappings = session.get("column_mappings", {})
        valid_files = [f for f in session.get("last_files", []) if os.path.isfile(f)]
        missing = [f for f in session.get("last_files", []) if not os.path.isfile(f)]
        for f in missing:
            self._toast.show_message(self._i18n.t("file_not_found", file=os.path.basename(f)))
        if valid_files:
            self._load_files(valid_files)

    def _save_session(self):
        config = self._search_panel.get_config()
        session = {
            **config,
            "last_files": list(self._loaded_files.keys()),
            "column_mappings": self._column_mappings,
            "view_mode": self._results_view.get_view_mode(),
            "window_size": [self.width(), self.height()],
            "window_position": [self.x(), self.y()],
            "ui_language": self._i18n.language,
        }
        self._session.save(session)

    def closeEvent(self, event):
        self._save_session()
        super().closeEvent(event)
