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

    def delete(self, note_id: str, device_id: str | None = None) -> None:
        """소프트 삭제: 실제 행을 지우지 않고 ``deleted_at`` 에 시각을 기록한다."""
        with get_session() as session:
            note = session.get(Note, note_id)
            if note is not None:
                now = datetime.now()
                note.deleted_at = now
                note.updated_at = now
                if device_id is not None:
                    note.last_synced_by = device_id

    def list_all(self, order_by: str = "updated_at",
                 pinned_first: bool = True) -> list[Note]:
        # 정렬 컬럼 화이트리스트로 SQL 인젝션 방지.
        column = {
            "updated_at": Note.updated_at,
            "created_at": Note.created_at,
            "title": Note.title,
        }.get(order_by, Note.updated_at)

        with get_session() as session:
            stmt = select(Note).where(Note.deleted_at.is_(None))
            order_cols = []
            if pinned_first:
                order_cols.append(Note.is_pinned.desc())
            # 수동 정렬 순서를 우선 적용하고, 동률은 선택 컬럼으로 정렬.
            order_cols.append(Note.sort_order.asc())
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
                "WHERE notes_fts MATCH :q AND n.deleted_at IS NULL "
                "ORDER BY rank"
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
                    .where(Note.note_type == note_type,
                           Note.deleted_at.is_(None))
                    .order_by(Note.is_pinned.desc(), Note.sort_order.asc(),
                              Note.updated_at.desc()))
            return list(session.scalars(stmt).all())

    def reorder(self, ordered_ids: list[str]) -> None:
        """주어진 노트 id 순서대로 ``sort_order`` 값을 0,1,2… 로 갱신한다.

        드래그 앤 드롭으로 순서를 바꾼 뒤 호출한다. ``updated_at`` 은 건드리지
        않아 정렬 변경이 동기화 충돌(LWW)에 영향을 주지 않도록 한다.
        """
        with get_session() as session:
            for index, note_id in enumerate(ordered_ids):
                note = session.get(Note, note_id)
                if note is not None:
                    note.sort_order = index

    # ----- 동기화 지원 -----------------------------------------------------
    def list_changed_since(self, since: datetime | None) -> list[Note]:
        """``since`` 이후 변경된(삭제 포함) 노트를 반환한다.

        ``since`` 가 ``None`` 이면 전체를 반환한다. 동기화 push 수집에 사용한다.
        """
        with get_session() as session:
            stmt = select(Note)
            if since is not None:
                stmt = stmt.where(
                    (Note.updated_at > since) | (Note.deleted_at > since)
                )
            return list(session.scalars(stmt).all())

    def upsert_remote(self, record: dict) -> None:
        """원격(서버) 노트 레코드를 로컬에 그대로 반영한다(LWW 적용 후 호출).

        ``record`` 는 id/title/body/note_type/updated_at/created_at/is_pinned/
        color_hint/deleted_at 키를 가질 수 있다.
        """
        with get_session() as session:
            note = session.get(Note, record["id"])
            if note is None:
                note = Note(id=record["id"])
                session.add(note)
            note.title = record.get("title", note.title or "제목 없음")
            note.body = record.get("body", note.body or "")
            note.note_type = record.get("note_type", note.note_type or "IDEA")
            note.is_pinned = bool(record.get("is_pinned", note.is_pinned))
            note.color_hint = record.get("color_hint", note.color_hint)
            if record.get("sort_order") is not None:
                note.sort_order = record["sort_order"]
            note.updated_at = record.get("updated_at", note.updated_at)
            if record.get("created_at") is not None:
                note.created_at = record["created_at"]
            note.deleted_at = record.get("deleted_at")
            note.last_synced_by = record.get("last_synced_by",
                                             note.last_synced_by)
