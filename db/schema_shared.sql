-- 서버·로컬 공용 스키마(Zettelkasten Sync).
--
-- 로컬 앱(db/database.py)과 클라우드 서버(server/database_server.py)가 동일한
-- 기본 테이블 구조를 공유한다. 동기화 전용 컬럼(last_synced_by, deleted_at)은
-- 양쪽 모두 초기화 단계에서 ALTER 로 추가한다(가드된 마이그레이션 참고).

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
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
    USING fts5(title, body, content='notes',
               content_rowid='rowid', tokenize='unicode61');

DROP TRIGGER IF EXISTS notes_ai;
DROP TRIGGER IF EXISTS notes_au;
DROP TRIGGER IF EXISTS notes_ad;

CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body)
    VALUES('delete', old.rowid, old.title, old.body);
    INSERT INTO notes_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body)
    VALUES('delete', old.rowid, old.title, old.body);
END;

CREATE TABLE IF NOT EXISTS tags (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL,
    color TEXT
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

CREATE TABLE IF NOT EXISTS note_links (
    source_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    link_type  TEXT NOT NULL DEFAULT 'related'
               CHECK(link_type IN ('related','supports','contradicts')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, target_id)
);

CREATE TABLE IF NOT EXISTS pdf_assets (
    id             TEXT PRIMARY KEY,
    file_path      TEXT NOT NULL,
    title          TEXT NOT NULL,
    thumbnail      BLOB,
    extracted_text TEXT,
    note_id        TEXT REFERENCES notes(id) ON DELETE SET NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classification_cache (
    note_id        TEXT PRIMARY KEY REFERENCES notes(id) ON DELETE CASCADE,
    suggested_tags TEXT,
    cluster_id     INTEGER,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
