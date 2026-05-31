"""Application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from db.database import init_db
from services.theme_service import get_theme_service
from ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("Zettelkasten")
    # 사용자 테마(또는 기본값)를 전역 스타일로 적용한다.
    get_theme_service().apply()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
