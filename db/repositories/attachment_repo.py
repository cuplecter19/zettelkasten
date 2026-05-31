"""Repository layer for :class:`core.attachment.Attachment`."""

from __future__ import annotations

import logging

from sqlalchemy import select

from core.attachment import Attachment, new_uuid
from db.database import get_session

logger = logging.getLogger(__name__)


class AttachmentRepository:
    """노트 첨부 자산 CRUD 를 담당하는 저장소."""

    def create(self, note_id: str, file_path: str, file_type: str,
               thumbnail: bytes | None = None) -> Attachment:
        with get_session() as session:
            attachment = Attachment(
                id=new_uuid(),
                note_id=note_id,
                file_path=file_path,
                file_type=file_type or "other",
                thumbnail=thumbnail,
            )
            session.add(attachment)
            session.flush()
            session.refresh(attachment)
            return attachment

    def get_by_id(self, attachment_id: str) -> Attachment | None:
        with get_session() as session:
            return session.get(Attachment, attachment_id)

    def list_for_note(self, note_id: str) -> list[Attachment]:
        with get_session() as session:
            stmt = (select(Attachment)
                    .where(Attachment.note_id == note_id)
                    .order_by(Attachment.created_at.asc()))
            return list(session.scalars(stmt).all())

    def first_image_for_note(self, note_id: str) -> Attachment | None:
        """노트의 첫 이미지 첨부(썸네일 표시용)를 반환한다."""
        with get_session() as session:
            stmt = (select(Attachment)
                    .where(Attachment.note_id == note_id,
                           Attachment.file_type == "image")
                    .order_by(Attachment.created_at.asc())
                    .limit(1))
            return session.scalars(stmt).first()

    def has_attachments(self, note_id: str) -> bool:
        with get_session() as session:
            stmt = (select(Attachment.id)
                    .where(Attachment.note_id == note_id)
                    .limit(1))
            return session.scalars(stmt).first() is not None

    def update_thumbnail(self, attachment_id: str, thumbnail: bytes) -> None:
        with get_session() as session:
            attachment = session.get(Attachment, attachment_id)
            if attachment is not None:
                attachment.thumbnail = thumbnail

    def delete(self, attachment_id: str) -> None:
        with get_session() as session:
            attachment = session.get(Attachment, attachment_id)
            if attachment is not None:
                session.delete(attachment)
