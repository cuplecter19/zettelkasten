"""SQLAlchemy ORM model for the ``tags`` and ``note_tags`` tables."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

from db.base import Base

# 노트-태그 다대다 연결 테이블.
note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", String, ForeignKey("notes.id", ondelete="CASCADE"),
           primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"),
           primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(Text, unique=True, nullable=False)
    color: str | None = Column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Tag id={self.id!r} name={self.name!r}>"
