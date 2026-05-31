"""Phase 6: 설정 다이얼로그 대시보드 탭 테스트."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository
from services.dashboard_service import DashboardService
from ui.dialogs.settings_dashboard_tab import SettingsDashboardTab


def test_tab_shows_totals(qtbot, db):
    repo = NoteRepository()
    repo.create("a", "", "IDEA")
    repo.create("b", "", "LEARNING")

    tab = SettingsDashboardTab(DashboardService())
    qtbot.addWidget(tab)
    assert tab._values["total_notes"].text() == "2"
    assert tab._values["type:LEARNING"].text() == "1"
    assert tab._values["type:IDEA"].text() == "1"


def test_refresh_picks_up_new_notes(qtbot, db):
    repo = NoteRepository()
    tab = SettingsDashboardTab(DashboardService())
    qtbot.addWidget(tab)
    assert tab._values["total_notes"].text() == "0"

    repo.create("c", "", "IDEA")
    tab.refresh()
    assert tab._values["total_notes"].text() == "1"
