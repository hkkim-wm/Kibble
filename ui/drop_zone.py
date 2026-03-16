import os

from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QEvent
from PyQt6.QtWidgets import QLabel, QWidget

from ui.i18n import I18n

VALID_EXTENSIONS = {".xlsx", ".csv", ".txt"}


class DropZoneFilter(QWidget):
    """Event filter that enables drag & drop on the entire main window."""

    files_dropped = pyqtSignal(list)
    invalid_files_dropped = pyqtSignal(list)

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self._i18n = i18n

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.DragEnter:
            mime = event.mimeData()
            if mime.hasUrls():
                event.acceptProposedAction()
                return True

        if event.type() == QEvent.Type.Drop:
            mime = event.mimeData()
            if mime.hasUrls():
                valid_paths = []
                invalid_paths = []
                for url in mime.urls():
                    path = url.toLocalFile()
                    ext = os.path.splitext(path)[1].lower()
                    if ext in VALID_EXTENSIONS:
                        valid_paths.append(path)
                    else:
                        invalid_paths.append(path)
                if valid_paths:
                    self.files_dropped.emit(valid_paths)
                if invalid_paths:
                    self.invalid_files_dropped.emit(invalid_paths)
                event.acceptProposedAction()
                return True

        return super().eventFilter(obj, event)


class ToastNotification(QLabel):
    """Non-blocking toast notification that auto-dismisses after 4 seconds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background-color: #333; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 12px;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)

    def show_message(self, message: str, duration_ms: int = 4000):
        self.setText(message)
        self.adjustSize()
        if self.parent():
            parent = self.parent()
            x = (parent.width() - self.width()) // 2
            y = parent.height() - self.height() - 40
            self.move(x, y)
        self.setVisible(True)
        self.raise_()
        self._timer.start(duration_ms)

    def _dismiss(self):
        self.setVisible(False)
