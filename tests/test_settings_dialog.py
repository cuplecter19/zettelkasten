"""Phase 1-2 / 1-3: 설정 다이얼로그 및 디자인 탭 단위 테스트."""

from __future__ import annotations

from services.css_snippet_service import CssSnippetService
from services.dashboard_service import DashboardService
from services.markdown_style_service import MarkdownStyleService
from services.theme_service import THEME_LABELS, ThemeService
from ui.dialogs.settings_dialog import CATEGORIES, SettingsDialog


def _theme(tmp_path) -> ThemeService:
    return ThemeService(tmp_path / "theme.json")


def _dialog(tmp_path) -> SettingsDialog:
    return SettingsDialog(
        theme=ThemeService(tmp_path / "theme.json"),
        markdown_style=MarkdownStyleService(tmp_path / "markdown_style.json"),
        css_snippets=CssSnippetService(tmp_path / "css_snippets.json"),
        dashboard=DashboardService(),
    )


def test_dialog_lists_all_categories(qtbot, tmp_path):
    dialog = SettingsDialog(theme=_theme(tmp_path))
    qtbot.addWidget(dialog)
    assert dialog._list.count() == len(CATEGORIES)
    assert dialog._stack.count() == len(CATEGORIES)
    assert dialog._list.currentRow() == 0


def test_dialog_switches_stack_on_selection(qtbot, tmp_path):
    dialog = SettingsDialog(theme=_theme(tmp_path))
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(2)
    assert dialog._stack.currentIndex() == 2


def test_design_tab_has_swatch_per_color(qtbot, tmp_path):
    dialog = SettingsDialog(theme=_theme(tmp_path))
    qtbot.addWidget(dialog)
    assert len(dialog._design_tab._swatches) == len(THEME_LABELS)


def test_design_tab_swatch_follows_theme_change(qtbot, tmp_path):
    theme = _theme(tmp_path)
    dialog = SettingsDialog(theme=theme)
    qtbot.addWidget(dialog)
    theme.set_color("accent", "#abcdef")
    assert dialog._design_tab._swatches["accent"].color == "#abcdef"


def test_dialog_wires_markdown_and_css_tabs(qtbot, tmp_path):
    dialog = _dialog(tmp_path)
    qtbot.addWidget(dialog)
    # 디자인/마크다운/CSS 스니펫/대시보드 탭이 순서대로 배치된다(Phase 6).
    assert dialog._markdown_tab is dialog._stack.widget(1)
    assert dialog._css_tab is dialog._stack.widget(2)
    assert dialog._dashboard_tab is dialog._stack.widget(3)
    assert dialog._stack.count() == len(CATEGORIES)
