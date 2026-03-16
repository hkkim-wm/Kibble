from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd

from core.parser import parse_file, detect_columns


class ParseWorker(QThread):
    """Background worker for file parsing."""

    finished = pyqtSignal(str, pd.DataFrame, str, list)  # file_path, df, source_col, target_cols
    error = pyqtSignal(str, str)  # file_path, error_message
    extra_sheets = pyqtSignal(str, int)  # file_path, sheet_count

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path

    def run(self):
        try:
            df = parse_file(self._file_path)
            source, targets = detect_columns(df)

            extra = df.attrs.get("extra_sheets", 0)
            if extra > 0:
                self.extra_sheets.emit(self._file_path, extra)

            self.finished.emit(self._file_path, df, source, targets)
        except ValueError as e:
            self.error.emit(self._file_path, str(e))
        except Exception as e:
            self.error.emit(self._file_path, f"Could not read {self._file_path}: {e}")
