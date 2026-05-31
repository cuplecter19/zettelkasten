"""Repository layer for :class:`core.note.Note`.

All database access for notes goes through this class. UI/service code must not
issue raw SQL or ORM queries directly.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, text

from core.note import Note, new_uuid
from db.database import get_session

logger = logging.getLogger(__name__)

# update() 로 변경 가능한 컬럼 화이트리스트.
_UPDATABLE_FIELDS = {
    "title", "body", "note_type", "is_pinned", "color_hint",
}


def _fts_query(query: str) -> str:
    """사용자 입력을 안전한 FTS5 MATCH 식으로 변환한다.

    각 토큰을 큰따옴표로 감싸 FTS5 특수 문법 해석을 방지하고 접두사 검색을
    적용한다.
    """
    tokens = [t for t in query.split() if t.strip()]
    safe_tokens = []
    for token in tokens:
        escaped = token.replace('"', '""')
        safe_tokens.append(f'"{escaped}"*')
    return " ".join(safe_tokens)


class NoteRepository:
    """노트 CRUD 및 검색을 담당하는 저장소."""

    def create(self, title: str, body: str, note_type: str) -> Note:
        with get_session() as session:
            note = Note(
                id=new_uuid(),
                title=title or "제목 없음",
                body=body or "",
                note_type=note_type or "IDEA",
                updated_at=datetime.now(),
            )
            session.add(note)
            session.flush()
            session.refresh(note)
            return note

    def get_by_id(self, note_id: str) -> Note | None:
        with get_session() as session:
            return session.get(Note, note_id)

    def update(self, note_id: str, **kwargs) -> Note:
        with get_session() as session:
            note = session.get(Note, note_id)
            if note is None:
                raise ValueError(f"Note not found: {note_id}")
            for key, value in kwargs.items():
                if key in _UPDATABLE_FIELDS:
                    setattr(note, key, value)
                else:
                    logger.warning("Ignoring non-updatable field %r", key)
            note.updated_at = datetime.now()
            session.flush()
            session.refresh(note)
            return note

    def delete(self, note_id: str) -> None:
        with get_session() as session:
            note = session.get(Note, note_id)
            if note is not None:
                session.delete(note)

    def list_all(self, order_by: str = "updated_at",
                 pinned_first: bool = True) -> list[Note]:
        # 정렬 컬럼 화이트리스트로 SQL 인젝션 방지.
        column = {
            "updated_at": Note.updated_at,
            "created_at": Note.created_at,
            "title": Note.title,
        }.get(order_by, Note.updated_at)

        with get_session() as session:
            stmt = select(Note)
            order_cols = []
            if pinned_first:
                order_cols.append(Note.is_pinned.desc())
            order_cols.append(column.desc())
            stmt = stmt.order_by(*order_cols)
            return list(session.scalars(stmt).all())

    def search_fts(self, query: str) -> list[Note]:
        match_expr = _fts_query(query)
        if not match_expr:
            return []
        with get_session() as session:
            sql = text(
                "SELECT n.id FROM notes_fts f "
                "JOIN notes n ON n.rowid = f.rowid "
                "WHERE notes_fts MATCH :q ORDER BY rank"
            )
            ids = [row[0] for row in session.execute(sql, {"q": match_expr})]
            if not ids:
                return []
            notes = session.scalars(select(Note).where(Note.id.in_(ids))).all()
            by_id = {n.id: n for n in notes}
            return [by_id[i] for i in ids if i in by_id]

    def get_by_type(self, note_type: str) -> list[Note]:
        with get_session() as session:
            stmt = (select(Note)
                    .where(Note.note_type == note_type)
                    .order_by(Note.is_pinned.desc(), Note.updated_at.desc()))
            return list(session.scalars(stmt).all())
