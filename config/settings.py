"""애플리케이션 전역 설정값."""

from pathlib import Path

APP_DIR              = Path.home() / ".zettelkasten"
DB_PATH              = APP_DIR / "notes.db"
PDF_DIR              = APP_DIR / "pdfs"
THEME                = "dark"        # "dark" | "light"
FONT_SIZE            = 14            # pt
QUICK_CAPTURE_HOTKEY = "ctrl+shift+n"
CLUSTER_MIN_NOTES    = 50
