import os
import re
import time
from typing import Dict, List, Any, Optional

import keyboard
import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog, QStatusBar,
    QLabel, QHBoxLayout, QPushButton, QMessageBox, QApplication,
    QMenuBar,
)

from core.parser import detect_columns, check_entry_limit, normalize_column_name, classify_column
from core.search import SearchConfig
from core.session import SessionManager
from ui.i18n import I18n
from ui.search_panel import SearchPanel
from ui.file_tabs import FileTabs
from ui.results_table import ResultsTableModel, ResultsTableView
from ui.drop_zone import DropZoneFilter, ToastNotification
from ui.column_mapper import ColumnMapperDialog
from workers.parse_worker import ParseWorker
from workers.search_worker import SearchWorker

APP_VERSION = "2.0"
HANGUL_RE = re.compile(r"[\uAC00-\uD7AF]")


GLOBAL_HOTKEY = "ctrl+shift+k"


class MainWindow(QMainWindow):
    # Signal to receive text from global hotkey (thread-safe bridge)
    _global_search_signal = pyqtSignal(str)

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

        # Search state
        self._search_texts: Optional[pd.Series] = None
        self._search_meta_df: Optional[pd.DataFrame] = None
        self._last_table_data: List[Dict[str, Any]] = []
        self._last_current_file: str = "all"
        self._last_search_direction: str = "source"
        self._last_search_query: str = ""
        self._last_filter_text: str = ""

        # Search timing
        self._search_start_time: float = 0

        # Session
        exe_dir = os.path.dirname(os.path.abspath(__file__))
        fallback = os.path.join(os.environ.get("APPDATA", ""), "Kibble")
        self._session = SessionManager(primary_dir=exe_dir, fallback_dir=fallback)

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_shortcuts()
        self._setup_global_hotkey()
        self._try_restore_session()

    def _setup_ui(self):
        self.setWindowTitle("Kibble")
        self.resize(1200, 800)
        self.setAcceptDrops(True)

        # Kibble theme — warm, professional palette
        self.setStyleSheet("""
            QMainWindow { background: #FAFAF8; }
            QMenuBar { background: #5B4A3F; color: #F5F0EB; padding: 2px; }
            QMenuBar::item:selected { background: #7A6555; border-radius: 3px; }
            QMenu { background: #FAFAF8; border: 1px solid #D4C8BC; }
            QMenu::item:selected { background: #E8DDD3; }
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab { background: #EDE7E0; color: #5B4A3F; padding: 6px 14px;
                           border: 1px solid #D4C8BC; border-bottom: none;
                           border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FAFAF8; font-weight: bold; }
            QTabBar::tab:hover { background: #F5F0EB; }
            QPushButton { background: #5B4A3F; color: #F5F0EB; border: none;
                          padding: 5px 12px; border-radius: 3px; }
            QPushButton:hover { background: #7A6555; }
            QPushButton:pressed { background: #4A3B32; }
            QLineEdit, QComboBox, QSpinBox { border: 1px solid #D4C8BC; border-radius: 3px;
                                              padding: 4px 6px; background: white; }
            QLineEdit:focus, QComboBox:focus { border-color: #8B7355; }
            QCheckBox, QRadioButton { color: #3D3028; }
            QTableView { gridline-color: #E8E0D8; alternate-background-color: #F9F6F2;
                         selection-background-color: #D4C8BC; selection-color: #3D3028; }
            QHeaderView::section { background: #EDE7E0; color: #5B4A3F; padding: 4px;
                                   border: 1px solid #D4C8BC; font-weight: bold; }
            QStatusBar { background: #EDE7E0; color: #5B4A3F; }
            QSlider::groove:horizontal { background: #D4C8BC; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #8B7355; width: 12px; height: 12px;
                                         margin: -4px 0; border-radius: 6px; }
            QLabel { color: #3D3028; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Search panel
        self._search_panel = SearchPanel(self._i18n)
        self._search_panel.search_requested.connect(self._on_search_requested)
        self._search_panel.filter_changed.connect(self._render_table)

        # File tabs
        self._file_tabs = FileTabs(self._i18n)
        self._file_tabs.file_closed.connect(self._on_file_closed)
        self._file_tabs.configure_requested.connect(self._on_configure_columns)

        # Layout: search panel, file tabs, results table
        layout.addWidget(self._search_panel)
        layout.addWidget(self._file_tabs)

        # Results table
        self._table_model = ResultsTableModel(self._i18n)
        self._results_view = ResultsTableView(self._i18n)
        self._results_view.set_model(self._table_model)
        self._results_view.view_mode_changed.connect(self._on_view_mode_changed)
        layout.addWidget(self._results_view, stretch=1)

        # Toast notification
        self._toast = ToastNotification(central)

        # Drop zone filter
        self._drop_filter = DropZoneFilter(self._i18n)
        self._drop_filter.files_dropped.connect(self._on_files_dropped)
        self._drop_filter.invalid_files_dropped.connect(self._on_invalid_files_dropped)
        self.installEventFilter(self._drop_filter)

        # Status bar
        status_bar = QStatusBar()
        self._lang_btn = QPushButton("EN | 한국어")
        self._lang_btn.setFixedWidth(100)
        self._lang_btn.clicked.connect(self._toggle_language)
        status_bar.addWidget(self._lang_btn)
        self._drop_hint = QLabel(self._i18n.t('drop_hint'))
        status_bar.addWidget(self._drop_hint, stretch=1)
        self._search_status = QLabel("")
        status_bar.addWidget(self._search_status)
        self._hotkey_hint = QLabel(self._i18n.t("global_hotkey"))
        self._hotkey_hint.setStyleSheet("color: #888; font-size: 11px;")
        status_bar.addPermanentWidget(self._hotkey_hint)
        self._status_info = QLabel(f"Kibble v{APP_VERSION}")
        status_bar.addPermanentWidget(self._status_info)
        self.setStatusBar(status_bar)

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu(self._i18n.t("menu_file"))
        self._open_action = QAction(self._i18n.t("menu_open"), self)
        self._open_action.setShortcut("Ctrl+O")
        self._open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(self._open_action)
        self._open_folder_action = QAction(self._i18n.t("menu_open_folder"), self)
        self._open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(self._open_folder_action)
        file_menu.addSeparator()
        self._exit_action = QAction(self._i18n.t("menu_exit"), self)
        self._exit_action.triggered.connect(self.close)
        file_menu.addAction(self._exit_action)
        self._file_menu = file_menu

        # Help menu
        help_menu = menu_bar.addMenu(self._i18n.t("menu_help"))
        self._about_action = QAction(self._i18n.t("menu_about"), self)
        self._about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(self._about_action)
        self._help_menu = help_menu

    def _show_about_dialog(self):
        QMessageBox.about(
            self,
            self._i18n.t("about_title"),
            self._i18n.t("about_text", version=APP_VERSION),
        )

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self._search_panel.focus_search)
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_file_dialog)
        QShortcut(QKeySequence("Ctrl+C"), self, self._results_view.copy_selected)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Escape"), self, self._search_panel.clear_search)

    def _setup_global_hotkey(self):
        """Register Ctrl+Shift+K as a system-wide hotkey."""
        self._global_search_signal.connect(self._on_global_search)
        try:
            keyboard.add_hotkey(GLOBAL_HOTKEY, self._on_hotkey_pressed, suppress=False)
        except Exception:
            pass  # Silently fail if hotkey registration fails (e.g. no admin)

    def _on_hotkey_pressed(self):
        """Called from keyboard listener thread.

        User copies text with Ctrl+C first, then presses Ctrl+Shift+K.
        We just signal the Qt thread to read the clipboard and search.
        """
        self._global_search_signal.emit("")

    def _on_global_search(self, _unused: str):
        """Handle global hotkey — runs on Qt main thread."""
        self._read_clipboard_and_search()

    def _read_clipboard_and_search(self):
        """Read clipboard via Qt and trigger search."""
        clipboard = QApplication.clipboard()
        text = (clipboard.text() or "").strip()
        if len(text) < 2:
            return
        # Bring window to foreground
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized
        )
        self.show()
        self.activateWindow()
        self.raise_()
        # Set text and search
        self._search_panel.set_search_and_trigger(text)

    def _toggle_language(self):
        new_lang = "en" if self._i18n.language == "ko" else "ko"
        self._i18n.set_language(new_lang)
        self._update_all_translations()

    def _update_all_translations(self):
        self._search_panel.update_translations()
        self._file_tabs.update_translations()
        self._results_view.update_translations()
        self._drop_hint.setText(f"\U0001F415 {self._i18n.t('drop_hint')}")
        self._hotkey_hint.setText(self._i18n.t("global_hotkey"))
        # Menu bar
        self._file_menu.setTitle(self._i18n.t("menu_file"))
        self._open_action.setText(self._i18n.t("menu_open"))
        self._open_folder_action.setText(self._i18n.t("menu_open_folder"))
        self._exit_action.setText(self._i18n.t("menu_exit"))
        self._help_menu.setTitle(self._i18n.t("menu_help"))
        self._about_action.setText(self._i18n.t("menu_about"))

    # --- Search animation ---

    def _start_search_animation(self):
        self._search_start_time = time.time()
        self._search_status.setText(self._i18n.t("searching"))

    def _stop_search_animation(self):
        elapsed = time.time() - self._search_start_time
        self._search_status.setText(f"{elapsed:.2f}s")

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

    def _open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, self._i18n.t("menu_open_folder"), "")
        if folder:
            supported_exts = (".xlsx", ".csv", ".txt")
            file_paths = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, f))
                and f.lower().endswith(supported_exts)
            ]
            if file_paths:
                self._load_files(file_paths)

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
        target_norm = {t: normalize_column_name(t) for t in targets}
        self._column_mappings[path] = {
            "source": source,
            "targets": targets,
            "target_norm": target_norm,
        }
        self._total_entries += len(df)

        display_name = os.path.basename(path)
        self._file_tabs.add_file_tab(path, display_name)
        self._update_status()

        self._results_view.set_target_languages(self._get_ordered_targets())

        sample = " ".join(str(v) for v in df[source].head(5).dropna())
        if not HANGUL_RE.search(sample):
            dialog = ColumnMapperDialog(df, self._i18n, source, targets, parent=self)
            if dialog.exec():
                new_source, new_targets = dialog.get_mapping()
                new_norm = {t: normalize_column_name(t) for t in new_targets}
                self._column_mappings[path] = {
                    "source": new_source,
                    "targets": new_targets,
                    "target_norm": new_norm,
                }

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
            norm = {t: normalize_column_name(t) for t in targets}
            self._column_mappings[current] = {
                "source": source,
                "targets": targets,
                "target_norm": norm,
            }

    # --- Search ---

    def _get_target_search_col(self, mapping: dict) -> str:
        """Return the original column name to search in for target direction."""
        target_norm = mapping.get("target_norm", {})
        # Reverse map: normalized code → original column name
        norm_to_orig = {v: k for k, v in target_norm.items()}

        view_mode = self._results_view.get_view_mode()
        if view_mode == "three_column":
            selected = self._results_view.get_selected_target_language()
            if selected:
                # selected is a normalized code; find original column
                if selected in norm_to_orig:
                    return norm_to_orig[selected]
                if selected in mapping.get("targets", []):
                    return selected
        targets = mapping.get("targets", [])
        return targets[0] if targets else ""

    def _on_search_requested(self, config: dict):
        if self._search_worker:
            self._search_worker.cancel()
            try:
                self._search_worker.finished.disconnect()
            except TypeError:
                pass
            if self._search_worker.isRunning():
                self._search_worker.wait(500)

        texts, meta_df = self._build_search_data(
            config["direction"],
            self._file_tabs.get_current_file(),
        )

        if len(texts) == 0:
            self._last_table_data = []
            self._table_model.clear()
            return

        search_config = SearchConfig(
            query=config["query"],
            mode=config["mode"],
            threshold=config["threshold"],
            limit=config["limit"],
            case_sensitive=config["case_sensitive"],
            wildcards=config["wildcards"],
            ignore_spaces=config.get("ignore_spaces", False),
            whole_word=config.get("whole_word", False),
        )

        self._search_texts = texts
        self._search_meta_df = meta_df
        self._last_search_query = config["query"]
        self._last_filter_text = config.get("filter_text", "")
        self._last_search_direction = config.get("direction", "source")

        self._start_search_animation()

        self._search_worker = SearchWorker(texts, search_config)
        self._search_worker.finished.connect(
            lambda results, count: self._on_search_finished(results, count, config)
        )
        self._search_worker.start()

    def _build_search_data(self, direction: str, file_filter: str):
        """Build search texts (pd.Series) and metadata (pd.DataFrame) — fully vectorized."""
        frames = []

        files = (
            list(self._loaded_files.items())
            if file_filter == "all"
            else [(file_filter, self._loaded_files[file_filter])]
            if file_filter in self._loaded_files
            else []
        )

        for path, df in files:
            mapping = self._column_mappings.get(path, {})
            source_col = mapping.get("source", df.columns[0])

            if direction == "source":
                search_col = source_col
            else:
                search_col = self._get_target_search_col(mapping)
                if not search_col or search_col not in df.columns:
                    search_col = source_col

            # Build a sub-dataframe with normalized column names
            target_cols = mapping.get("targets", [])
            target_norm = mapping.get("target_norm", {})

            sub = pd.DataFrame()
            sub["_search_text"] = df[search_col].fillna("").astype(str) if search_col in df.columns else ""
            sub["_source"] = df[source_col].fillna("").astype(str) if source_col in df.columns else ""
            for t in target_cols:
                if t in df.columns:
                    norm = target_norm.get(t, t)
                    if norm in sub.columns:
                        # Another column already mapped to this normalized name;
                        # keep the first non-empty value
                        existing = sub[norm]
                        new_vals = df[t].fillna("").astype(str)
                        sub[norm] = existing.where(existing != "", new_vals)
                    else:
                        sub[norm] = df[t].fillna("").astype(str)
            sub["_file_path"] = path
            sub["_file_name"] = os.path.basename(path)

            # Filter out empty search texts
            sub = sub[sub["_search_text"] != ""].reset_index(drop=True)
            frames.append(sub)

        if not frames:
            return pd.Series(dtype=str), pd.DataFrame()

        meta_df = pd.concat(frames, ignore_index=True)
        # Fill NaN from mismatched columns across different files
        meta_df = meta_df.fillna("")
        texts = meta_df["_search_text"]
        return texts, meta_df

    def _on_search_finished(self, results: list, total_hits: int, config: dict):
        self._stop_search_animation()

        try:
            self._process_search_results(results, total_hits, config)
        except Exception as e:
            self._last_table_data = []
            self._table_model.clear()
            self._toast.show_message(f"Search error: {e}")

    def _process_search_results(self, results: list, total_hits: int, config: dict):
        meta_df = self._search_meta_df
        if meta_df is None or meta_df.empty:
            self._last_table_data = []
            self._table_model.clear()
            return

        self._search_panel.set_total_hits(total_hits)

        # Build table data using vectorized indexing
        indices = [r["index"] for r in results]
        if not indices:
            self._last_table_data = []
            self._last_current_file = self._file_tabs.get_current_file()
            self._render_table()
            return

        matched = meta_df.iloc[indices].copy()
        matched = matched.reset_index(drop=True)

        current_file = self._file_tabs.get_current_file()
        scores = [r["score"] for r in results]
        table_data = []
        for i in range(len(matched)):
            row = {"source": str(matched.iloc[i]["_source"]), "_score": scores[i]}
            for col in matched.columns:
                if col.startswith("_"):
                    continue
                val = matched.iloc[i][col]
                row[col] = str(val) if val and str(val) != "nan" else ""
            if current_file == "all":
                row["meta"] = str(matched.iloc[i]["_file_name"])
            table_data.append(row)

        self._last_table_data = table_data
        self._last_current_file = current_file
        self._render_table()

    def _render_table(self):
        table_data = self._last_table_data
        current_file = self._last_current_file
        if not table_data:
            self._table_model.clear()
            self._search_panel.set_total_hits(0)
            return

        # Apply secondary filter
        filter_text = self._search_panel.get_filter_text().lower()
        direction = self._last_search_direction
        if filter_text:
            filtered_data = []
            for row in table_data:
                if direction == "source":
                    all_target_text = " ".join(
                        str(v) for k, v in row.items()
                        if k not in ("source", "meta")
                    ).lower()
                    if filter_text in all_target_text:
                        filtered_data.append(row)
                else:
                    if filter_text in row.get("source", "").lower():
                        filtered_data.append(row)
            table_data = filtered_data

        self._search_panel.set_total_hits(len(table_data))

        view_mode = self._results_view.get_view_mode()
        ordered_targets = self._get_ordered_targets()
        all_targets = set(ordered_targets)

        if view_mode == "three_column":
            selected_lang = self._results_view.get_selected_target_language()
            if not selected_lang and ordered_targets:
                selected_lang = ordered_targets[0]
            visible_targets = [selected_lang] if selected_lang and selected_lang in all_targets else ordered_targets[:1]
        else:
            visible_targets = ordered_targets

        columns = [self._i18n.t("source_col")]
        columns.extend(visible_targets)
        if current_file == "all":
            columns.append(self._i18n.t("meta_info"))

        # Detect duplicate translations: same source text with different target translations
        # Only compare actual language columns; ignore empty cells (from files missing that language)
        from collections import defaultdict
        from core.parser import _LANG_CODES
        lang_targets = [t for t in visible_targets if t in _LANG_CODES]

        # Per-source, per-language: collect distinct non-empty translations
        source_lang_vals: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        for row in table_data:
            src = row.get("source", "")
            if src:
                for t in lang_targets:
                    val = row.get(t, "")
                    if val:
                        source_lang_vals[src][t].add(val)
        # Build per-source set of languages that have conflicting translations
        dup_source_langs: dict[str, set] = {}
        for src, lang_dict in source_lang_vals.items():
            conflict_langs = {lang for lang, vals in lang_dict.items() if len(vals) > 1}
            if conflict_langs:
                dup_source_langs[src] = conflict_langs

        display_data = []
        for row in table_data:
            score = row.get("_score", 0)
            src = row.get("source", "")
            conflict_langs = dup_source_langs.get(src, set())
            d = {
                "_score": score,
                "_score_num": score,
                "_is_dup": bool(conflict_langs),
                "_dup_langs": conflict_langs,
                self._i18n.t("source_col"): row.get("source", ""),
            }
            for t in visible_targets:
                d[t] = row.get(t, "")
            if current_file == "all":
                d[self._i18n.t("meta_info")] = row.get("meta", "")
            d["source"] = row.get("source", "")
            d["target"] = " | ".join(row.get(t, "") for t in visible_targets)
            display_data.append(d)

        self._table_model.set_results(display_data, columns)
        self._results_view.resize_score_column()

        # Set highlight queries: search query for source, filter text for targets
        self._results_view.set_highlight_queries(
            search_query=self._last_search_query,
            filter_query=self._search_panel.get_filter_text(),
            search_direction=self._last_search_direction,
        )

    def _on_view_mode_changed(self, mode: str):
        self._render_table()

    def _get_ordered_targets(self) -> list:
        """Collect normalized target columns: file-order languages, then info, then metadata.

        Processes the file with the most targets first so its column order
        becomes the canonical ordering. Additional targets from other files
        are inserted at the correct position relative to their neighbours.
        """
        # Sort mappings: most targets first to establish the best base order
        mappings = sorted(
            self._column_mappings.values(),
            key=lambda m: len(m.get("targets", [])),
            reverse=True,
        )
        seen = set()
        langs, info, meta = [], [], []
        for mapping in mappings:
            target_norm = mapping.get("target_norm", {})
            norms = [target_norm.get(t, t) for t in mapping.get("targets", [])]
            for i, norm in enumerate(norms):
                if norm in seen:
                    continue
                seen.add(norm)
                cls = classify_column(norm)
                bucket = langs if cls == 0 else info if cls == 1 else meta
                # Insert after the last already-added predecessor from this file
                insert_pos = len(bucket)
                for j in range(i - 1, -1, -1):
                    prev = norms[j]
                    if prev in bucket:
                        insert_pos = bucket.index(prev) + 1
                        break
                bucket.insert(insert_pos, norm)
        return langs + info + meta

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
        self._results_view.set_font_size(session.get("font_size", 12))
        self._column_mappings = session.get("column_mappings", {})
        # Rebuild normalized target mappings for sessions saved before this feature
        for path, mapping in self._column_mappings.items():
            if "target_norm" not in mapping:
                mapping["target_norm"] = {
                    t: normalize_column_name(t) for t in mapping.get("targets", [])
                }
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
            "font_size": self._results_view.get_font_size(),
            "window_size": [self.width(), self.height()],
            "window_position": [self.x(), self.y()],
            "ui_language": self._i18n.language,
        }
        self._session.save(session)

    def closeEvent(self, event):
        self._save_session()
        try:
            keyboard.remove_hotkey(GLOBAL_HOTKEY)
        except Exception:
            pass
        super().closeEvent(event)
