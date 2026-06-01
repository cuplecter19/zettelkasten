"""Application entry point."""

from __future__ import annotations

import logging
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from db.database import init_db
from services.theme_service import get_theme_service
from ui.main_window import MainWindow

if os.name == 'nt':
    log_dir = Path(os.environ['LOCALAPPDATA']) / "Zettelkasten"
else:
    log_dir = Path.home() / ".zettelkasten"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "app.log", encoding='utf-8'),
        logging.StreamHandler(),
    ]
)

def resource_path(relative_path: str) -> Path:
    """개발 환경과 PyInstaller 빌드 환경 모두에서 동작."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path

def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if sys.platform == 'win32':
        import ctypes
        myappid = 'zettelkasten'  # 임의의 고유 문자열
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("Zettelkasten")
    # 사용자 테마(또는 기본값)를 전역 스타일로 적용한다.
    app.setWindowIcon(QIcon(str(resource_path("resources/icon.ico"))))
    get_theme_service().apply()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
