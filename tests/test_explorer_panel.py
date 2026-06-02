"""Explorer panel filter button style tests."""

from __future__ import annotations

from ui.panels.explorer_panel import ExplorerPanel


def test_filter_button_checked_style_has_no_border():
    style = ExplorerPanel._pill_style(object(), "IDEA")

    assert "QPushButton:checked { border: none; }" in style
    assert "QPushButton:checked { border: 2px" not in style


def test_note_list_matches_search_background_style(qtbot, db):
    panel = ExplorerPanel()
    qtbot.addWidget(panel)

    style = panel._list.styleSheet()

    assert "QListWidget#NoteList" in style
    assert "background-color:" in style
    assert "border-radius: 12px" in style
