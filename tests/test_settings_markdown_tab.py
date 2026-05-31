"""Phase 4: 설정 다이얼로그 마크다운 탭 테스트."""

from __future__ import annotations

from services.markdown_style_service import (MARKDOWN_ELEMENTS,
                                             MarkdownStyleService)
from ui.dialogs.settings_markdown_tab import SettingsMarkdownTab


def _style(tmp_path) -> MarkdownStyleService:
    return MarkdownStyleService(tmp_path / "markdown_style.json")


def test_tab_has_row_per_element(qtbot, tmp_path):
    tab = SettingsMarkdownTab(_style(tmp_path))
    qtbot.addWidget(tab)
    assert len(tab._rows) == len(MARKDOWN_ELEMENTS)


def test_spinbox_change_updates_service(qtbot, tmp_path):
    style = _style(tmp_path)
    tab = SettingsMarkdownTab(style)
    qtbot.addWidget(tab)
    tab._rows["h1"]["size"].setValue(40)
    assert style.get_style("h1")["font_size"] == 40


def test_tab_exposes_list_and_table_rows(qtbot, tmp_path):
    tab = SettingsMarkdownTab(_style(tmp_path))
    qtbot.addWidget(tab)
    for element in ("ul", "table", "th", "td"):
        assert element in tab._rows


def test_checkbox_change_updates_service(qtbot, tmp_path):
    style = _style(tmp_path)
    tab = SettingsMarkdownTab(style)
    qtbot.addWidget(tab)
    tab._rows["p"]["bold"].setChecked(True)
    assert style.get_style("p")["bold"] is True


def test_widgets_follow_external_change(qtbot, tmp_path):
    style = _style(tmp_path)
    tab = SettingsMarkdownTab(style)
    qtbot.addWidget(tab)
    style.set_field("h2", "font_size", 30)
    assert tab._rows["h2"]["size"].value() == 30
