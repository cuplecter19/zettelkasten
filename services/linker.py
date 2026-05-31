"""Note linking service: similarity-based suggestions and explicit links."""

from __future__ import annotations

import logging

from sqlalchemy import select

from core.link import NoteLink
from core.note import Note
from db.database import get_session
from db.repositories.note_repo import NoteRepository

logger = logging.getLogger(__name__)

VALID_LINK_TYPES = {"related", "supports", "contradicts"}


class LinkerService:
    """TF-IDF 유사도 기반 연결 제안과 명시적 링크 관리."""

    def __init__(self) -> None:
        self._notes = NoteRepository()

    def suggest_links(self, note_id: str, top_n: int = 5) -> list[Note]:
        """TF-IDF 코사인 유사도로 유사 노트 top_n개 반환."""
        target = self._notes.get_by_id(note_id)
        if target is None:
            return []

        all_notes = [n for n in self._notes.list_all() if n.id != note_id]
        if not all_notes:
            return []

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [f"{target.title}\n{target.body}"] + [
            f"{n.title}\n{n.body}" for n in all_notes]
        try:
            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return []

        sims = cosine_similarity(matrix[0], matrix[1:]).ravel()
        ranked = sorted(
            ((score, idx) for idx, score in enumerate(sims) if score > 0.0),
            reverse=True,
        )[:top_n]
        return [all_notes[idx] for _score, idx in ranked]

    def create_link(self, source_id: str, target_id: str,
                    link_type: str = "related") -> None:
        if link_type not in VALID_LINK_TYPES:
            raise ValueError(f"Invalid link_type: {link_type}")
        if source_id == target_id:
            raise ValueError("Cannot link a note to itself.")

        with get_session() as session:
            existing = session.get(NoteLink, (source_id, target_id))
            if existing is None:
                session.add(NoteLink(source_id=source_id, target_id=target_id,
                                     link_type=link_type))
            else:
                existing.link_type = link_type

    def get_links(self, note_id: str) -> dict:
        """``{'outgoing': [...], 'incoming': [...]}`` 형태로 반환."""
        with get_session() as session:
            outgoing_ids = list(session.scalars(
                select(NoteLink.target_id).where(NoteLink.source_id == note_id)))
            incoming_ids = list(session.scalars(
                select(NoteLink.source_id).where(NoteLink.target_id == note_id)))

            def fetch(ids: list[str]) -> list[Note]:
                if not ids:
                    return []
                return list(session.scalars(
                    select(Note).where(Note.id.in_(ids))).all())

            return {"outgoing": fetch(outgoing_ids),
                    "incoming": fetch(incoming_ids)}
