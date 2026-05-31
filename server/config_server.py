"""클라우드 동기화 서버 설정값.

배포 시 민감한 값(SECRET_KEY 등)과 경로는 환경변수로 덮어쓸 수 있다.
"""

from __future__ import annotations

import os
from pathlib import Path

SERVER_DIR   = Path(os.environ.get("ZK_SERVER_DIR", "/opt/zettelkasten"))
DB_PATH      = Path(os.environ.get("ZK_SERVER_DB", str(SERVER_DIR / "server.db")))
PDF_DIR      = Path(os.environ.get("ZK_SERVER_PDF_DIR", str(SERVER_DIR / "pdfs")))
SECRET_KEY   = os.environ.get("SECRET_KEY", "CHANGE_ME_ON_DEPLOY")  # 배포 시 교체
TOKEN_EXPIRE = int(os.environ.get("TOKEN_EXPIRE", "1440"))          # 분(24시간)
ALGORITHM    = "HS256"

# 허용 기기 목록(쉼표 구분). 비어 있으면 모든 기기 ID 의 토큰 발급을 허용한다.
ALLOWED_DEVICES = [
    d.strip() for d in os.environ.get("ALLOWED_DEVICES", "").split(",") if d.strip()
]
