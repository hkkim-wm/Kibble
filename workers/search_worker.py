from typing import List, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.search import search, SearchConfig


class SearchWorker(QThread):
    """Background worker for search execution."""

    finished = pyqtSignal(list, int)  # results, total_hits
    cancelled = pyqtSignal()

    def __init__(self, entries: List[Dict[str, Any]], config: SearchConfig, parent=None):
        super().__init__(parent)
        self._entries = entries
        self._config = config
        self._cancelled = False

    def run(self):
        if self._cancelled:
            self.cancelled.emit()
            return
        results = search(self._entries, self._config)
        if self._cancelled:
            self.cancelled.emit()
            return
        self.finished.emit(results, len(results))

    def cancel(self):
        self._cancelled = True
