"""무압박 첫 화면 오버레이 테스트."""

from __future__ import annotations

from PySide6.QtCore import Qt

from ui.widgets.startup_dashboard import StartupDashboardOverlay


def test_startup_dashboard_has_styled_background(qtbot):
    overlay = StartupDashboardOverlay("#abcdef")
    qtbot.addWidget(overlay)

    assert overlay.objectName() == "StartupDashboardOverlay"
    assert overlay.testAttribute(Qt.WA_StyledBackground)


def test_startup_dashboard_fades_out_on_click(qtbot):
    overlay = StartupDashboardOverlay("#abcdef")
    qtbot.addWidget(overlay)
    overlay.show()

    qtbot.mouseClick(overlay, Qt.LeftButton)

    assert overlay._animation.state() == overlay._animation.Running
