"""High-level search service combining FTS5 full-text and tag search."""

from __future__ import annotations

import logging

from core.note import Note
from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository

logger = logging.getLogger(__name__)


class SearchService:
    """전문 검색·태그 검색·복합 검색을 제공한다."""

    def __init__(self) -> None:
        self._notes = NoteRepository()
        self._tags = TagRepository()

    def full_text_search(self, query: str) -> list[Note]:
        if not query or not query.strip():
            return []
        return self._notes.search_fts(query)

    def tag_search(self, tag_name: str) -> list[Note]:
        if not tag_name or not tag_name.strip():
            return []
        return self._tags.get_notes_for_tag(tag_name)

    def combined_search(self, query: str, note_type: str | None = None,
                        tags: list[str] | None = None) -> list[Note]:
        # 기본 후보군: 검색어가 있으면 FTS, 없으면 전체.
        if query and query.strip():
            results = self._notes.search_fts(query)
        else:
            results = self._notes.list_all()

        if note_type:
            results = [n for n in results if n.note_type == note_type]

        if tags:
            allowed_ids: set[str] | None = None
            for tag_name in tags:
                tag_note_ids = {n.id for n in self._tags.get_notes_for_tag(tag_name)}
                allowed_ids = (tag_note_ids if allowed_ids is None
                               else allowed_ids & tag_note_ids)
            allowed_ids = allowed_ids or set()
            results = [n for n in results if n.id in allowed_ids]

        return results
