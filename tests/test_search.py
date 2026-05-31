"""Tests for FTS5-backed search."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository
from services.search_service import SearchService


def test_fts_finds_created_note(db):
    repo = NoteRepository()
    note = repo.create("파이썬 알고리즘", "이진 탐색 알고리즘 정리", "LEARNING")

    service = SearchService()
    results = service.full_text_search("알고리즘")

    assert any(n.id == note.id for n in results)


def test_fts_returns_empty_for_missing_keyword(db):
    repo = NoteRepository()
    repo.create("자수 도안", "구매한 패턴 보관", "ARCHIVE")

    service = SearchService()
    assert service.full_text_search("존재하지않는키워드xyz") == []


def test_fts_blank_query_returns_empty(db):
    service = SearchService()
    assert service.full_text_search("   ") == []


def test_combined_search_filters_by_type(db):
    repo = NoteRepository()
    learning = repo.create("학습 노트", "알고리즘 공부", "LEARNING")
    repo.create("기분 노트", "오늘 알고리즘 같은 하루 우울", "MOOD")

    service = SearchService()
    results = service.combined_search("알고리즘", note_type="LEARNING")

    ids = {n.id for n in results}
    assert learning.id in ids
    assert all(n.note_type == "LEARNING" for n in results)
