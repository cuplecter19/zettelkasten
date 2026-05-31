"""연결되지 않은 노트 주간 수집 서비스 테스트."""

from __future__ import annotations

from datetime import date

from core.link import NoteLink
from db.database import get_session
from db.repositories.note_repo import NoteRepository
from services.orphan_service import OrphanCollectorService


def test_collect_orphans_excludes_linked_notes(db, tmp_path):
    repo = NoteRepository()
    orphan = repo.create("orphan", "", "IDEA")
    source = repo.create("source", "", "IDEA")
    target = repo.create("target", "", "IDEA")
    with get_session() as session:
        session.add(NoteLink(source_id=source.id, target_id=target.id))

    service = OrphanCollectorService(tmp_path / "orphans.json")
    assert [note.id for note in service.collect_orphans()] == [orphan.id]


def test_collect_orphans_excludes_deleted_notes(db, tmp_path):
    repo = NoteRepository()
    note = repo.create("deleted", "", "IDEA")
    repo.delete(note.id)

    service = OrphanCollectorService(tmp_path / "orphans.json")
    assert service.collect_orphans() == []


def test_weekly_due_state_is_persisted(tmp_path):
    path = tmp_path / "orphans.json"
    service = OrphanCollectorService(path)
    assert service.is_due(date(2026, 5, 1)) is True

    service.mark_checked(date(2026, 5, 1))
    assert service.is_due(date(2026, 5, 7)) is False
    assert service.is_due(date(2026, 5, 8)) is True

    reloaded = OrphanCollectorService(path)
    assert reloaded.last_checked == date(2026, 5, 1)
