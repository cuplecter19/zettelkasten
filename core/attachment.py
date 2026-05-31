"""SQLAlchemy ORM model for the ``attachments`` table."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (DateTime, ForeignKey, LargeBinary, String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


def new_uuid() -> str:
    """새 첨부 자산용 UUID 문자열 생성."""
    return str(uuid.uuid4())


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    note_id: Mapped[str] = mapped_column(
        String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False, default="other")
    thumbnail: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp())

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (f"<Attachment id={self.id!r} note_id={self.note_id!r} "
                f"type={self.file_type!r}>")
