"""Phase 2-3: notes.sort_order 마이그레이션 및 드래그 순서 변경 테스트."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository


def test_new_notes_have_default_sort_order(db):
    repo = NoteRepository()
    note = repo.create("A", "본문", "IDEA")
    fetched = repo.get_by_id(note.id)
    assert fetched.sort_order == 0


def test_reorder_persists_sort_order(db):
    repo = NoteRepository()
    a = repo.create("A", "x", "IDEA")
    b = repo.create("B", "y", "IDEA")
    c = repo.create("C", "z", "IDEA")

    repo.reorder([c.id, a.id, b.id])

    assert repo.get_by_id(c.id).sort_order == 0
    assert repo.get_by_id(a.id).sort_order == 1
    assert repo.get_by_id(b.id).sort_order == 2


def test_list_all_orders_by_sort_order(db):
    repo = NoteRepository()
    a = repo.create("A", "x", "IDEA")
    b = repo.create("B", "y", "IDEA")
    c = repo.create("C", "z", "IDEA")

    repo.reorder([c.id, a.id, b.id])
    ordered = [n.title for n in repo.list_all()]
    assert ordered == ["C", "A", "B"]


def test_pinned_notes_float_to_top(db):
    repo = NoteRepository()
    a = repo.create("A", "x", "IDEA")
    b = repo.create("B", "y", "IDEA")
    repo.reorder([a.id, b.id])
    repo.update(b.id, is_pinned=True)

    ordered = [n.title for n in repo.list_all()]
    assert ordered[0] == "B"  # 고정 노트가 sort_order 와 무관하게 최상단


def test_reorder_ignores_unknown_ids(db):
    repo = NoteRepository()
    a = repo.create("A", "x", "IDEA")
    # 존재하지 않는 id 가 섞여도 예외 없이 처리.
    repo.reorder(["missing", a.id])
    assert repo.get_by_id(a.id).sort_order == 1
