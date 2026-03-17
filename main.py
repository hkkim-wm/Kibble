import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def _get_icon_path() -> str:
    """Resolve icon path for both dev and PyInstaller onefile mode."""
    if getattr(sys, '_MEIPASS', None):
        # PyInstaller extracts to a temp dir
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", "icon.ico")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kibble")

    icon_path = _get_icon_path()
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
