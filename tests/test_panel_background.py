"""패널 루트 배경 스타일 적용 테스트."""

from __future__ import annotations

from PySide6.QtCore import Qt

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
