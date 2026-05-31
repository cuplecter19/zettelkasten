"""Phase 1-1: 커스텀 타이틀바 및 프레임리스 리사이즈 단위 테스트."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QMainWindow, QMenuBar

from ui.widgets.title_bar import (CustomTitleBar, FramelessResizer, _EdgeGrip)


def test_title_bar_has_window_buttons(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    bar = CustomTitleBar(window, title="제목", menu_widget=QMenuBar(window))
    assert bar._btn_min is not None
    assert bar._btn_max is not None
    assert bar._btn_close is not None
    bar.set_title("새 제목")
    assert bar._title_label.text() == "새 제목"


def test_title_bar_dots_use_specified_colors(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    bar = CustomTitleBar(window)
    # 빨강=종료, 주황=최소화, 초록=최대화.
    assert CustomTitleBar.DOT_CLOSE in bar._btn_close.styleSheet()
    assert CustomTitleBar.DOT_MINIMIZE in bar._btn_min.styleSheet()
    assert CustomTitleBar.DOT_MAXIMIZE in bar._btn_max.styleSheet()
    # 도트는 작은 원형 버튼이다.
    assert bar._btn_close.width() == bar._btn_close.height()


def test_title_bar_double_click_toggles_without_error(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    bar = CustomTitleBar(window)
    # 예외 없이 토글이 동작해야 한다.
    bar.toggle_maximize()
    bar.toggle_maximize()


def test_edge_grip_left_resizes_left_edge(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setMinimumSize(200, 150)
    grip = _EdgeGrip(window, Qt.LeftEdge)
    start = QRect(100, 100, 800, 600)  # left=100, right=899
    # 왼쪽 가장자리를 오른쪽으로 50px 끌면 left 가 증가, right 는 고정.
    geom = grip._compute_geometry(start, 50, 0)
    assert geom.left() == 150
    assert geom.right() == start.right()


def test_edge_grip_respects_minimum_width(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setMinimumSize(200, 150)
    grip = _EdgeGrip(window, Qt.RightEdge)
    start = QRect(0, 0, 800, 600)
    # 오른쪽 가장자리를 과도하게 왼쪽으로 끌어도 최소 너비를 보장.
    geom = grip._compute_geometry(start, -10000, 0)
    assert geom.width() >= 200


def test_frameless_resizer_positions_handles(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.resize(500, 400)
    resizer = FramelessResizer(window, margin=6)
    resizer.reposition()
    left = resizer._edges[Qt.LeftEdge]
    right = resizer._edges[Qt.RightEdge]
    assert left.geometry().left() == 0
    assert right.geometry().x() == window.width() - 6
