"""SQLAlchemy ORM model for the ``pdf_assets`` table."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


def new_uuid() -> str:
    """새 PDF 자산용 UUID 문자열 생성."""
    return str(uuid.uuid4())


class PdfAsset(Base):
    __tablename__ = "pdf_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    note_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp())
    # 동기화 메타데이터.
    last_synced_by: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<PdfAsset id={self.id!r} title={self.title!r}>"
