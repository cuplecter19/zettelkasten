"""Phase 5: 설정 다이얼로그 CSS 스니펫 탭 테스트."""

from __future__ import annotations

from PySide6.QtCore import Qt

from services.css_snippet_service import CssSnippetService
from ui.dialogs.settings_css_tab import SettingsCssTab


def _service(tmp_path) -> CssSnippetService:
    return CssSnippetService(tmp_path / "css_snippets.json")


def test_add_creates_list_item(qtbot, tmp_path):
    service = _service(tmp_path)
    tab = SettingsCssTab(service)
    qtbot.addWidget(tab)
    assert tab._list.count() == 0
    tab._add()
    assert tab._list.count() == 1
    assert len(service.list_snippets()) == 1


def test_editor_change_updates_snippet(qtbot, tmp_path):
    service = _service(tmp_path)
    tab = SettingsCssTab(service)
    qtbot.addWidget(tab)
    tab._add()
    tab._editor.setPlainText(".md-h1 { color: green; }")
    assert service.get_snippet(tab._current_id)["css"] == ".md-h1 { color: green; }"


def test_uncheck_disables_snippet(qtbot, tmp_path):
    service = _service(tmp_path)
    tab = SettingsCssTab(service)
    qtbot.addWidget(tab)
    tab._add()
    item = tab._list.item(0)
    item.setCheckState(Qt.Unchecked)
    assert service.get_snippet(tab._current_id)["enabled"] is False


def test_remove_clears_selection(qtbot, tmp_path):
    service = _service(tmp_path)
    tab = SettingsCssTab(service)
    qtbot.addWidget(tab)
    tab._add()
    tab._remove()
    assert tab._list.count() == 0
    assert service.list_snippets() == []


def test_existing_snippets_loaded(qtbot, tmp_path):
    service = _service(tmp_path)
    service.add_snippet("미리", ".md-p { line-height: 1.6; }")
    tab = SettingsCssTab(service)
    qtbot.addWidget(tab)
    assert tab._list.count() == 1
    assert tab._editor.toPlainText() == ".md-p { line-height: 1.6; }"
