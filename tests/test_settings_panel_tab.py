"""설정 다이얼로그 패널 모드 탭 단위 테스트."""

from __future__ import annotations

from services.panel_service import DASHBOARD_PANELS, PanelService
from ui.dialogs.settings_panel_tab import SettingsPanelTab


def _service(tmp_path) -> PanelService:
    return PanelService(tmp_path / "panels.json")


def test_tab_has_checkbox_per_panel(qtbot, tmp_path):
    tab = SettingsPanelTab(_service(tmp_path))
    qtbot.addWidget(tab)
    assert set(tab._checks) == set(DASHBOARD_PANELS)
    assert all(check.isChecked() for check in tab._checks.values())


def test_toggle_updates_service(qtbot, tmp_path):
    svc = _service(tmp_path)
    tab = SettingsPanelTab(svc)
    qtbot.addWidget(tab)
    tab._checks["summary"].setChecked(False)
    assert svc.is_enabled("summary") is False


def test_tab_follows_service_change(qtbot, tmp_path):
    svc = _service(tmp_path)
    tab = SettingsPanelTab(svc)
    qtbot.addWidget(tab)
    svc.set_enabled("by_type", False)
    assert tab._checks["by_type"].isChecked() is False
