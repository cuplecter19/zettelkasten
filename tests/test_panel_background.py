"""패널 루트 배경 스타일 적용 테스트."""

from __future__ import annotations

from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from ui.panels.graph_panel import GraphPanel
from ui.panels.pdf_panel import PDFPanel


def test_pdf_panel_has_styled_background(qtbot, db):
    panel = PDFPanel()
    qtbot.addWidget(panel)
    assert panel.objectName() == "PDFPanel"
    assert panel.testAttribute(Qt.WA_StyledBackground)


def test_graph_panel_has_styled_background(qtbot, db):
    panel = GraphPanel()
    qtbot.addWidget(panel)
    assert panel.objectName() == "GraphPanel"
    assert panel.testAttribute(Qt.WA_StyledBackground)


def test_suggestions_list_uses_editor_background(qtbot, db, monkeypatch):
    monkeypatch.setattr(MainWindow, "_setup_tray_and_hotkey", lambda self: None)
    monkeypatch.setattr(MainWindow, "_setup_sync", lambda self: None)
    monkeypatch.setattr(MainWindow, "_build_startup_dashboard", lambda self: None)
    monkeypatch.setattr(MainWindow, "_show_weekly_orphans", lambda self: None)

    window = MainWindow()
    qtbot.addWidget(window)

    panel = window._suggestions.parentWidget()
    assert panel.objectName() == "SuggestionsPanel"
    assert panel.testAttribute(Qt.WA_StyledBackground)
    assert window._suggestions.objectName() == "SuggestedNotesList"
    assert "QListWidget#SuggestedNotesList" in window.styleSheet()
    assert "border-radius: 12px" in window.styleSheet()
