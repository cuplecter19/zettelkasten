"""Database engine, session factory and raw-SQL schema bootstrap.

The schema (including the FTS5 virtual table and its sync triggers) is created
with raw SQL exactly as specified in the work order. ORM models in ``core`` map
onto these tables for convenience but are not used to create them.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import APP_DIR, DB_PATH, PDF_DIR

logger = logging.getLogger(__name__)

# 동기화 전용 컬럼(서버·로컬 공용). 기존 DB 에도 누락 시 ALTER 로 추가한다.
# 각 항목: (테이블, 컬럼, 컬럼 정의)
SYNC_COLUMNS: list[tuple[str, str, str]] = [
    ("notes", "last_synced_by", "TEXT"),
    ("notes", "deleted_at", "DATETIME"),
    ("pdf_assets", "last_synced_by", "TEXT"),
    ("pdf_assets", "deleted_at", "DATETIME"),
]

# 전체 스키마 정의(노트/FTS5/트리거/태그/링크/PDF/분류 캐시).
SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS notes (
        id          TEXT PRIMARY KEY,
        title       TEXT NOT NULL DEFAULT '제목 없음',
        body        TEXT NOT NULL DEFAULT '',
        note_type   TEXT NOT NULL DEFAULT 'IDEA'
                    CHECK(note_type IN ('LEARNING','IDEA','MOOD','ARCHIVE')),
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME,
        is_pinned   BOOLEAN NOT NULL DEFAULT 0,
        color_hint  TEXT
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
        USING fts5(title, body, content='notes',
                   content_rowid='rowid', tokenize='unicode61')
    """,
    """
    CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
        INSERT INTO notes_fts(rowid, title, body)
        VALUES (new.rowid, new.title, new.body);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
        UPDATE notes_fts SET title=new.title, body=new.body WHERE rowid=old.rowid;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
        DELETE FROM notes_fts WHERE rowid=old.rowid;
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT UNIQUE NOT NULL,
        color TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS note_tags (
        note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
        tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
        PRIMARY KEY (note_id, tag_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS note_links (
        source_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
        target_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
        link_type  TEXT NOT NULL DEFAULT 'related'
                   CHECK(link_type IN ('related','supports','contradicts')),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (source_id, target_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pdf_assets (
        id             TEXT PRIMARY KEY,
        file_path      TEXT NOT NULL,
        title          TEXT NOT NULL,
        thumbnail      BLOB,
        extracted_text TEXT,
        note_id        TEXT REFERENCES notes(id) ON DELETE SET NULL,
        created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS classification_cache (
        note_id        TEXT PRIMARY KEY REFERENCES notes(id) ON DELETE CASCADE,
        suggested_tags TEXT,
        cluster_id     INTEGER,
        updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

# 엔진/세션 팩토리는 init_db() 에서 초기화된다.
_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _enable_sqlite_fks(dbapi_connection, _connection_record) -> None:
    """SQLite 의 외래 키 제약을 연결마다 활성화한다."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def ensure_sync_columns(conn: Connection) -> None:
    """동기화 전용 컬럼이 없으면 ALTER 로 추가한다(가드된 마이그레이션).

    서버·로컬 양쪽에서 재사용한다. 이미 존재하는 DB 파일에도 안전하게 적용된다.
    """
    for table, column, definition in SYNC_COLUMNS:
        existing = {
            row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
        }
        if column not in existing:
            conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            logger.info("Added sync column %s.%s", table, column)


def init_db(db_path: Path | str = DB_PATH) -> Engine:
    """엔진/세션 팩토리를 초기화하고 스키마를 생성한다.

    앱 데이터 폴더(``~/.zettelkasten`` 및 ``pdfs/``)가 없으면 자동 생성한다.
    """
    global _engine, _SessionFactory

    db_path = Path(db_path)
    # 메모리 DB(테스트용)가 아닐 때만 디스크 폴더를 준비한다.
    if db_path != Path(":memory:") and str(db_path) != ":memory:":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(f"sqlite:///{db_path}", future=True)
    event.listen(_engine, "connect", _enable_sqlite_fks)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False,
                                   future=True)

    with _engine.begin() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(text(statement))
        ensure_sync_columns(conn)

    logger.info("Database initialised at %s", db_path)
    return _engine


def get_engine() -> Engine:
    """초기화된 엔진을 반환한다."""
    if _engine is None:
        raise RuntimeError("init_db() must be called before get_engine().")
    return _engine


@contextmanager
def get_session() -> Iterator[Session]:
    """트랜잭션을 자동 커밋/롤백하는 세션 컨텍스트 매니저."""
    if _SessionFactory is None:
        raise RuntimeError("init_db() must be called before get_session().")
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
