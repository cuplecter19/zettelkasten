"""Repository layer for :class:`core.tag.Tag` and note-tag associations."""

from __future__ import annotations

import logging

from sqlalchemy import delete, insert, select

from core.note import Note
from core.tag import Tag, note_tags
from db.database import get_session

logger = logging.getLogger(__name__)


class TagRepository:
    """태그 CRUD 및 노트-태그 연결을 담당하는 저장소."""

    def get_or_create(self, name: str, color: str | None = None) -> Tag:
        name = name.strip()
        with get_session() as session:
            tag = session.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name, color=color)
                session.add(tag)
                session.flush()
                session.refresh(tag)
            return tag

    def list_all(self) -> list[Tag]:
        with get_session() as session:
            return list(session.scalars(select(Tag).order_by(Tag.name)).all())

    def get_by_name(self, name: str) -> Tag | None:
        with get_session() as session:
            return session.scalar(select(Tag).where(Tag.name == name.strip()))

    def delete(self, tag_id: int) -> None:
        with get_session() as session:
            tag = session.get(Tag, tag_id)
            if tag is not None:
                session.delete(tag)

    def add_tag_to_note(self, note_id: str, tag_name: str,
                        color: str | None = None) -> Tag:
        tag = self.get_or_create(tag_name, color)
        with get_session() as session:
            exists = session.execute(
                select(note_tags).where(
                    note_tags.c.note_id == note_id,
                    note_tags.c.tag_id == tag.id,
                )
            ).first()
            if exists is None:
                session.execute(
                    insert(note_tags).values(note_id=note_id, tag_id=tag.id))
        return tag

    def remove_tag_from_note(self, note_id: str, tag_id: int) -> None:
        with get_session() as session:
            session.execute(
                delete(note_tags).where(
                    note_tags.c.note_id == note_id,
                    note_tags.c.tag_id == tag_id,
                )
            )

    def get_tags_for_note(self, note_id: str) -> list[Tag]:
        with get_session() as session:
            stmt = (select(Tag)
                    .join(note_tags, note_tags.c.tag_id == Tag.id)
                    .where(note_tags.c.note_id == note_id)
                    .order_by(Tag.name))
            return list(session.scalars(stmt).all())

    def get_notes_for_tag(self, tag_name: str) -> list[Note]:
        with get_session() as session:
            stmt = (select(Note)
                    .join(note_tags, note_tags.c.note_id == Note.id)
                    .join(Tag, Tag.id == note_tags.c.tag_id)
                    .where(Tag.name == tag_name.strip())
                    .order_by(Note.is_pinned.desc(), Note.updated_at.desc()))
            return list(session.scalars(stmt).all())
