"""서버 DB 초기화 및 연결 관리.

로컬 앱과 동일한 공용 스키마(``db/schema_shared.sql``)를 사용하고, 동기화
전용 컬럼(last_synced_by, deleted_at)을 추가한다. 동시 사용자가 2명뿐이므로
SQLite 로 충분하다.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine

from config_server import DB_PATH, PDF_DIR

logger = logging.getLogger(__name__)

# 동기화 전용 컬럼(서버·로컬 공용). 누락 시 ALTER 로 추가한다.
SYNC_COLUMNS: list[tuple[str, str, str]] = [
    ("notes", "last_synced_by", "TEXT"),
    ("notes", "deleted_at", "DATETIME"),
    ("pdf_assets", "last_synced_by", "TEXT"),
    ("pdf_assets", "deleted_at", "DATETIME"),
]

# 공용 스키마 파일 후보 경로. Docker 이미지(/app/db) 와 저장소 레이아웃 모두 지원.
_SCHEMA_CANDIDATES = [
    Path(__file__).resolve().parent / "db" / "schema_shared.sql",
    Path(__file__).resolve().parent.parent / "db" / "schema_shared.sql",
    Path("/app/db/schema_shared.sql"),
]

_engine: Engine | None = None


def _schema_path() -> Path:
    for candidate in _SCHEMA_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "schema_shared.sql 을 찾을 수 없습니다. "
        f"확인한 경로: {[str(p) for p in _SCHEMA_CANDIDATES]}"
    )


def _enable_sqlite_fks(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _ensure_sync_columns(conn: Connection) -> None:
    for table, column, definition in SYNC_COLUMNS:
        existing = {
            row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
        }
        if column not in existing:
            conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            logger.info("Added sync column %s.%s", table, column)


def init_server_db() -> Engine:
    """서버 DB 를 초기화한다. ``db/schema_shared.sql`` 실행 후 동기화 컬럼 추가."""
    global _engine

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    event.listen(_engine, "connect", _enable_sqlite_fks)

    schema_sql = _schema_path().read_text(encoding="utf-8")
    with _engine.begin() as conn:
        # SQLite 는 executescript 가 필요하므로 raw 연결로 실행한다.
        raw = conn.connection
        raw.executescript(schema_sql)
        _ensure_sync_columns(conn)

    logger.info("Server database initialised at %s", DB_PATH)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("init_server_db() must be called first.")
    return _engine


@contextmanager
def get_connection() -> Iterator[Connection]:
    """트랜잭션을 자동 커밋/롤백하는 연결 컨텍스트 매니저."""
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def db_dependency() -> Iterator[Connection]:
    """FastAPI ``Depends`` 용 연결 의존성."""
    with get_connection() as conn:
        yield conn
