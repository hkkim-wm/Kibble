from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QTabWidget, QPushButton,
)

from ui.i18n import I18n


class FileTabs(QWidget):
    """Tab widget with 'Search All' + per-file closable tabs + gear button."""

    tab_changed = pyqtSignal(str)  # Emits file path or "all"
    file_closed = pyqtSignal(str)  # Emits file path of closed tab
    configure_requested = pyqtSignal()  # Gear button clicked

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n
        self._file_paths: dict[int, str] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)

        # Hide the tab content area — we only use the tab bar for navigation
        self._tabs.setStyleSheet("QTabWidget::pane { border: none; max-height: 0px; }")

        # "Search All" tab (always first, not closable)
        self._tabs.addTab(QWidget(), self._i18n.t("search_all"))
        self._tabs.tabBar().setTabButton(0, self._tabs.tabBar().ButtonPosition.RightSide, None)
        layout.addWidget(self._tabs, stretch=1)

        # Gear button for column mapping
        self._gear_btn = QPushButton("⚙")
        self._gear_btn.setFixedWidth(32)
        self._gear_btn.setToolTip(self._i18n.t("configure_columns"))
        self._gear_btn.clicked.connect(self.configure_requested.emit)
        layout.addWidget(self._gear_btn)

    def add_file_tab(self, file_path: str, display_name: str) -> int:
        tab_index = self._tabs.addTab(QWidget(), display_name)
        self._file_paths[tab_index] = file_path
        return tab_index

    def remove_file_tab(self, file_path: str):
        for idx, path in list(self._file_paths.items()):
            if path == file_path:
                self._tabs.removeTab(idx)
                del self._file_paths[idx]
                self._reindex()
                break

    def _reindex(self):
        new_paths = {}
        ordered = sorted(self._file_paths.items(), key=lambda x: x[0])
        for new_idx, (_, path) in enumerate(ordered, start=1):
            new_paths[new_idx] = path
        self._file_paths = new_paths

    def _on_tab_changed(self, index: int):
        if index == 0:
            self.tab_changed.emit("all")
        elif index in self._file_paths:
            self.tab_changed.emit(self._file_paths[index])

    def _on_tab_close_requested(self, index: int):
        if index == 0:
            return
        if index in self._file_paths:
            self.file_closed.emit(self._file_paths[index])

    def get_current_file(self) -> str:
        index = self._tabs.currentIndex()
        if index == 0:
            return "all"
        return self._file_paths.get(index, "all")

    def get_loaded_files(self) -> list[str]:
        return list(self._file_paths.values())

    def update_translations(self):
        self._tabs.setTabText(0, self._i18n.t("search_all"))
        self._gear_btn.setToolTip(self._i18n.t("configure_columns"))
