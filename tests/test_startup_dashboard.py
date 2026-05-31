"""무압박 첫 화면 오버레이 테스트."""

from __future__ import annotations

from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtGui import QImage

from ui.widgets.startup_dashboard import StartupDashboardOverlay


def test_startup_dashboard_has_styled_background(qtbot):
    overlay = StartupDashboardOverlay("#abcdef")
    qtbot.addWidget(overlay)

    assert overlay.objectName() == "StartupDashboardOverlay"
    assert overlay.testAttribute(Qt.WA_StyledBackground)
    assert overlay._message.isHidden() is False


def test_startup_dashboard_hides_message_when_image_exists(qtbot, tmp_path):
    image_path = tmp_path / "welcome.png"
    image = QImage(2, 2, QImage.Format_RGB32)
    image.fill(0xabcdef)
    assert image.save(str(image_path))

    overlay = StartupDashboardOverlay("#abcdef", str(image_path))
    qtbot.addWidget(overlay)

    assert overlay._message.isHidden() is True


def test_startup_dashboard_fades_out_on_click(qtbot):
    overlay = StartupDashboardOverlay("#abcdef")
    qtbot.addWidget(overlay)
    overlay.show()

    qtbot.mouseClick(overlay, Qt.LeftButton)

    assert overlay._animation.state() == QAbstractAnimation.Running
