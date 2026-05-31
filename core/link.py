"""SQLAlchemy ORM model for the ``note_links`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class NoteLink(Base):
    __tablename__ = "note_links"

    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    target_id: Mapped[str] = mapped_column(
        String, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    link_type: Mapped[str] = mapped_column(String, nullable=False, default="related")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp())

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (f"<NoteLink {self.source_id!r} -> {self.target_id!r} "
                f"type={self.link_type!r}>")
