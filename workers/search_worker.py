import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from core.search import search_vectorized, SearchConfig


class SearchWorker(QThread):
    """Background worker for search execution."""

    finished = pyqtSignal(list, int)  # results, total_hits

    def __init__(self, texts: pd.Series, config: SearchConfig, parent=None):
        super().__init__(parent)
        self._texts = texts
        self._config = config
        self._cancelled = False

    def run(self):
        if self._cancelled:
            return
        result_df = search_vectorized(self._texts, self._config)
        if self._cancelled:
            return
        results = [
            {"index": int(row["index"]), "score": int(row["score"])}
            for _, row in result_df.iterrows()
        ]
        self.finished.emit(results, len(results))

    def cancel(self):
        self._cancelled = True
