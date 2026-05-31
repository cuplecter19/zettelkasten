"""Phase 6: 대시보드 통계 서비스 테스트."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository
from services.dashboard_service import DashboardService, _empty_stats


def test_empty_database_returns_zero_stats(db):
    stats = DashboardService().collect_stats()
    assert stats["total_notes"] == 0
    assert stats["by_type"] == {"LEARNING": 0, "IDEA": 0, "MOOD": 0, "ARCHIVE": 0}
    assert stats["total_tags"] == 0
    assert stats["untagged_notes"] == 0


def test_counts_notes_by_type_and_pinned(db):
    repo = NoteRepository()
    repo.create("a", "", "IDEA")
    learning = repo.create("b", "", "LEARNING")
    repo.create("c", "", "LEARNING")
    repo.update(learning.id, is_pinned=True)

    stats = DashboardService().collect_stats()
    assert stats["total_notes"] == 3
    assert stats["by_type"]["LEARNING"] == 2
    assert stats["by_type"]["IDEA"] == 1
    assert stats["pinned_notes"] == 1


def test_soft_deleted_notes_are_excluded(db):
    repo = NoteRepository()
    keep = repo.create("keep", "", "IDEA")
    drop = repo.create("drop", "", "IDEA")
    repo.delete(drop.id)

    stats = DashboardService().collect_stats()
    assert stats["total_notes"] == 1
    assert stats["by_type"]["IDEA"] == 1
    assert keep.id  # 사용된 변수 보장


def test_tag_and_untagged_counts(db):
    notes = NoteRepository()
    tags = TagRepository()
    tagged = notes.create("tagged", "", "IDEA")
    notes.create("untagged", "", "IDEA")
    tags.add_tag_to_note(tagged.id, "python")

    stats = DashboardService().collect_stats()
    assert stats["total_tags"] == 1
    assert stats["untagged_notes"] == 1


def test_collect_stats_without_db_is_safe():
    # init_db() 를 호출하지 않은 상태에서도 빈 통계를 반환해야 한다.
    assert DashboardService().collect_stats() == _empty_stats()


def test_dashboard_settings_are_persisted(tmp_path):
    path = tmp_path / "dashboard.json"
    service = DashboardService(path)
    service.set_welcome_color("#abcdef")
    service.set_welcome_image_path("/tmp/background.png")

    reloaded = DashboardService(path)
    assert reloaded.welcome_color() == "#abcdef"
    assert reloaded.welcome_image_path() == "/tmp/background.png"


def test_dashboard_rejects_invalid_color(tmp_path):
    service = DashboardService(tmp_path / "dashboard.json")
    original = service.welcome_color()
    service.set_welcome_color("not-a-color")
    assert service.welcome_color() == original
