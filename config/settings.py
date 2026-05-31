"""애플리케이션 전역 설정값."""

from pathlib import Path
import os

if os.name == 'nt':  # Windows
    APP_DIR = Path(os.environ['LOCALAPPDATA']) / "Zettelkasten"
else:
    APP_DIR = Path.home() / ".zettelkasten"
DB_PATH              = APP_DIR / "notes.db"
PDF_DIR              = APP_DIR / "pdfs"
THEME                = "dark"        # "dark" | "light"
FONT_SIZE            = 14            # pt
QUICK_CAPTURE_HOTKEY = "ctrl+shift+n"
CLUSTER_MIN_NOTES    = 50


SYNC_SERVER_URL  = os.environ.get("ZK_SYNC_SERVER_URL", "http://<서버IP>:8000")
DEVICE_ID        = os.environ.get("ZK_DEVICE_ID", "main-pc")  # 기기별 고유 값
SYNC_TOKEN       = os.environ.get("ZK_SYNC_TOKEN", "")        # 최초 인증 후 저장
SYNC_INTERVAL    = int(os.environ.get("ZK_SYNC_INTERVAL", "30"))  # 초
LAST_SYNC_AT     = None  # datetime. 앱 실행 시 로드/갱신한다.

