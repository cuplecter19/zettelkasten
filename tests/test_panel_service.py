"""대시보드 패널 모드 서비스 단위 테스트."""

from __future__ import annotations

import json

from services.panel_service import DASHBOARD_PANELS, PanelService


def _service(tmp_path) -> PanelService:
    return PanelService(tmp_path / "panels.json")


def test_all_panels_enabled_by_default(tmp_path):
    svc = _service(tmp_path)
    assert svc.enabled_panels() == list(DASHBOARD_PANELS)


def test_set_enabled_persists_and_emits(qtbot, tmp_path):
    svc = _service(tmp_path)
    received = []
    svc.panels_changed.connect(lambda: received.append(True))
    svc.set_enabled("summary", False)
    assert received
    assert svc.is_enabled("summary") is False
    data = json.loads((tmp_path / "panels.json").read_text(encoding="utf-8"))
    assert data["summary"] is False


def test_disabled_panel_excluded(tmp_path):
    svc = _service(tmp_path)
    svc.set_enabled("by_type", False)
    assert "by_type" not in svc.enabled_panels()
    assert "summary" in svc.enabled_panels()


def test_set_enabled_ignores_unknown_panel(tmp_path):
    svc = _service(tmp_path)
    svc.set_enabled("nope", False)
    assert "nope" not in svc.enabled_panels()


def test_reload_restores_state(tmp_path):
    svc = _service(tmp_path)
    svc.set_enabled("summary", False)
    reloaded = PanelService(tmp_path / "panels.json")
    assert reloaded.is_enabled("summary") is False
