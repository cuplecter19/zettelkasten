"""로컬 소프트 삭제 및 동기화 컬럼 동작 테스트."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository
from db.repositories.pdf_repo import PdfRepository


def test_note_soft_delete_hides_from_list(db):
    repo = NoteRepository()
    note = repo.create("삭제 대상", "본문", "IDEA")

    repo.delete(note.id, device_id="main-pc")

    # 목록/검색에서 제외되지만 행 자체는 남아 deleted_at 이 기록된다.
    assert all(n.id != note.id for n in repo.list_all())
    fetched = repo.get_by_id(note.id)
    assert fetched is not None
    assert fetched.deleted_at is not None
    assert fetched.last_synced_by == "main-pc"


def test_list_changed_since_includes_deleted(db):
    repo = NoteRepository()
    note = repo.create("변경 추적", "본문", "IDEA")
    repo.delete(note.id)

    changed = repo.list_changed_since(None)
    assert any(n.id == note.id and n.deleted_at is not None for n in changed)


def test_upsert_remote_overwrites_local(db):
    repo = NoteRepository()
    note = repo.create("로컬 제목", "로컬 본문", "IDEA")

    repo.upsert_remote({
        "id": note.id,
        "title": "서버 제목",
        "body": "서버 본문",
        "note_type": "LEARNING",
        "is_pinned": True,
        "color_hint": None,
        "updated_at": None,
        "deleted_at": None,
    })

    updated = repo.get_by_id(note.id)
    assert updated.title == "서버 제목"
    assert updated.note_type == "LEARNING"
    assert updated.is_pinned is True


def test_pdf_soft_delete_hides_from_list(db):
    repo = PdfRepository()
    asset = repo.create("/tmp/x.pdf", "샘플", None, None)

    repo.delete(asset.id, device_id="laptop")

    assert all(a.id != asset.id for a in repo.list_all())
    fetched = repo.get_by_id(asset.id)
    assert fetched is not None and fetched.deleted_at is not None
