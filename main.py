"""Application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from db.database import init_db
from ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("Zettelkasten")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
