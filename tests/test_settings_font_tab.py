"""설정 다이얼로그 폰트 탭 단위 테스트."""

from __future__ import annotations

from services.font_service import FONT_TARGETS, FontService
from ui.dialogs.settings_font_tab import SettingsFontTab


def _service(tmp_path) -> FontService:
    return FontService(tmp_path / "fonts.json", tmp_path / "fonts")


def test_tab_has_combo_per_target(qtbot, tmp_path):
    tab = SettingsFontTab(_service(tmp_path))
    qtbot.addWidget(tab)
    assert set(tab._combos) == set(FONT_TARGETS)


def test_combo_change_updates_service(qtbot, tmp_path):
    svc = _service(tmp_path)
    tab = SettingsFontTab(svc)
    qtbot.addWidget(tab)
    combo = tab._combos["h1"]
    # (기본) + 시스템 폰트가 채워져 있어야 한다.
    assert combo.count() >= 2
    combo.setCurrentIndex(1)
    assert svc.get_assignment("h1") == combo.currentData()


def test_tab_follows_service_change(qtbot, tmp_path):
    svc = _service(tmp_path)
    tab = SettingsFontTab(svc)
    qtbot.addWidget(tab)
    families = svc.available_families()
    if not families:
        return
    svc.set_assignment("p", families[0])
    assert tab._combos["p"].currentData() == families[0]
