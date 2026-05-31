"""그래프 뷰 Ctrl+휠 확대/축소 단위 테스트."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QWheelEvent

from ui.panels.graph_panel import (ZoomableGraphicsView, _ZOOM_MAX, _ZOOM_MIN)
from PySide6.QtWidgets import QGraphicsScene


def _view(qtbot) -> ZoomableGraphicsView:
    view = ZoomableGraphicsView(QGraphicsScene())
    qtbot.addWidget(view)
    return view


def test_zoom_by_increases_and_decreases(qtbot):
    view = _view(qtbot)
    assert view.zoom == 1.0
    view.zoom_by(1.5)
    assert view.zoom > 1.0
    view.reset_zoom()
    assert view.zoom == 1.0


def test_zoom_is_clamped(qtbot):
    view = _view(qtbot)
    view.zoom_by(1000.0)
    assert view.zoom <= _ZOOM_MAX
    view.zoom_by(0.00001)
    assert view.zoom >= _ZOOM_MIN


def _wheel(view, delta: int, ctrl: bool) -> QWheelEvent:
    mods = Qt.ControlModifier if ctrl else Qt.NoModifier
    return QWheelEvent(
        QPoint(10, 10), view.mapToGlobal(QPoint(10, 10)),
        QPoint(0, delta), QPoint(0, delta),
        Qt.NoButton, mods, Qt.ScrollUpdate, False)


def test_ctrl_wheel_zooms_in(qtbot):
    view = _view(qtbot)
    view.wheelEvent(_wheel(view, 120, ctrl=True))
    assert view.zoom > 1.0


def test_plain_wheel_does_not_zoom(qtbot):
    view = _view(qtbot)
    view.wheelEvent(_wheel(view, 120, ctrl=False))
    assert view.zoom == 1.0
