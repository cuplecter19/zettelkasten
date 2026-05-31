"""커스텀 타이틀바 및 프레임리스 창 리사이즈 유틸리티.

``QMainWindow`` 의 기본 제목 표시줄을 제거(``Qt.FramelessWindowHint``)했을 때
사용할 커스텀 타이틀바와 가장자리 리사이즈 핸들을 제공한다.

- :class:`CustomTitleBar` : 제목, 최소화/최대화/닫기 버튼, 드래그 이동,
  더블클릭 최대화 토글.
- :func:`install_resize_handles` : 창 가장자리/모서리 리사이즈 핸들 설치.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSizeGrip,
                               QWidget)

# 가장자리 리사이즈 핸들 두께(px).
EDGE_MARGIN = 6


class CustomTitleBar(QWidget):
    """창 상단에 위치하는 커스텀 타이틀바.

    좌측 상단에는 macOS 스타일의 컬러 도트 3종을 두며, 각 도트는 창 제어
    버튼에 대응한다.

    - 빨강 도트 → 종료(닫기)
    - 주황 도트 → 최소화
    - 초록 도트 → 최대화(토글)

    그 우측으로 (선택적) 메뉴바와 제목을 배치한다. 빈 영역을 드래그하면 창을
    이동하고, 더블클릭하면 최대화를 토글한다.
    """

    # 도트 색상(테마와 무관하게 고정되는 기본 UI 색상).
    DOT_CLOSE = "#ff5f57"     # 빨강 · 종료
    DOT_MINIMIZE = "#ffab2e"  # 주황 · 최소화
    DOT_MAXIMIZE = "#28c840"  # 초록 · 최대화

    def __init__(self, window: QWidget, title: str = "Zettelkasten",
                 menu_widget: QWidget | None = None) -> None:
        super().__init__(window)
        self._window = window
        self._drag_offset: QPoint | None = None
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # 좌측 상단 컬러 도트 3종(닫기/최소화/최대화).
        self._btn_close = self._make_dot(self.DOT_CLOSE, "종료")
        self._btn_close.setObjectName("TitleBarClose")
        self._btn_close.clicked.connect(self._window.close)
        layout.addWidget(self._btn_close)

        self._btn_min = self._make_dot(self.DOT_MINIMIZE, "최소화")
        self._btn_min.clicked.connect(self._window.showMinimized)
        layout.addWidget(self._btn_min)

        self._btn_max = self._make_dot(self.DOT_MAXIMIZE, "최대화")
        self._btn_max.clicked.connect(self.toggle_maximize)
        layout.addWidget(self._btn_max)

        layout.addSpacing(8)

        if menu_widget is not None:
            layout.addWidget(menu_widget)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("TitleBarLabel")
        layout.addWidget(self._title_label)
        layout.addStretch(1)

    # ----- 구성 -----------------------------------------------------------
    def _make_dot(self, color: str, tooltip: str) -> QPushButton:
        """지정한 색상의 원형 창 제어 도트 버튼을 만든다."""
        btn = QPushButton("", self)
        btn.setToolTip(tooltip)
        btn.setFixedSize(14, 14)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setCursor(Qt.PointingHandCursor)
        # 전역 QSS(QPushButton)의 영향을 받지 않도록 인라인 스타일로 색을 고정.
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; border: none;"
            " border-radius: 7px; }"
            f"QPushButton:hover {{ background-color: {color};"
            " border: 1px solid rgba(0, 0, 0, 0.35); }")
        return btn

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    # ----- 동작 -----------------------------------------------------------
    def toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    # ----- 창 드래그 이동 -------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton and not self._window.isMaximized():
            self._drag_offset = (event.globalPosition().toPoint()
                                 - self._window.frameGeometry().topLeft())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class _EdgeGrip(QWidget):
    """창 가장자리에서 드래그로 크기를 조절하는 얇은 핸들 위젯."""

    def __init__(self, window: QWidget, edge: Qt.Edge | Qt.Edges) -> None:
        super().__init__(window)
        self._window = window
        self._edge = edge
        self._press_global: QPoint | None = None
        self._start_geom = None
        horizontal = edge in (Qt.LeftEdge, Qt.RightEdge)
        self.setCursor(Qt.SizeHorCursor if horizontal else Qt.SizeVerCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton and not self._window.isMaximized():
            self._press_global = event.globalPosition().toPoint()
            self._start_geom = self._window.geometry()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._press_global is None or self._start_geom is None:
            return super().mouseMoveEvent(event)
        delta = event.globalPosition().toPoint() - self._press_global
        geom = self._compute_geometry(self._start_geom, delta.x(), delta.y())
        self._window.setGeometry(geom)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._press_global = None
        self._start_geom = None
        super().mouseReleaseEvent(event)

    def _compute_geometry(self, start, dx: int, dy: int):
        """시작 geometry 와 드래그 변위로 새 geometry 를 계산한다."""
        from PySide6.QtCore import QRect
        min_w = max(self._window.minimumWidth(), 200)
        min_h = max(self._window.minimumHeight(), 150)
        left, top = start.left(), start.top()
        right, bottom = start.right(), start.bottom()

        if self._edge & Qt.LeftEdge:
            left = min(left + dx, right - min_w)
        if self._edge & Qt.RightEdge:
            right = max(right + dx, left + min_w)
        if self._edge & Qt.TopEdge:
            top = min(top + dy, bottom - min_h)
        if self._edge & Qt.BottomEdge:
            bottom = max(bottom + dy, top + min_h)
        return QRect(QPoint(left, top), QPoint(right, bottom))


class FramelessResizer:
    """프레임리스 창에 가장자리/모서리 리사이즈 핸들을 부착해 관리한다."""

    def __init__(self, window: QWidget, margin: int = EDGE_MARGIN) -> None:
        self._window = window
        self._margin = margin
        self._edges = {
            Qt.LeftEdge: _EdgeGrip(window, Qt.LeftEdge),
            Qt.RightEdge: _EdgeGrip(window, Qt.RightEdge),
            Qt.TopEdge: _EdgeGrip(window, Qt.TopEdge),
            Qt.BottomEdge: _EdgeGrip(window, Qt.BottomEdge),
        }
        # 네 모서리는 네이티브 동작의 QSizeGrip 사용.
        self._corners = [QSizeGrip(window) for _ in range(4)]
        for grip in self._corners:
            grip.setFixedSize(margin * 2, margin * 2)

    def reposition(self) -> None:
        """창 크기에 맞춰 모든 핸들의 위치를 갱신한다(resizeEvent 에서 호출)."""
        w = self._window.width()
        h = self._window.height()
        m = self._margin
        self._edges[Qt.LeftEdge].setGeometry(0, m, m, h - 2 * m)
        self._edges[Qt.RightEdge].setGeometry(w - m, m, m, h - 2 * m)
        self._edges[Qt.TopEdge].setGeometry(m, 0, w - 2 * m, m)
        self._edges[Qt.BottomEdge].setGeometry(m, h - m, w - 2 * m, m)
        c = self._corners
        size = m * 2
        c[0].move(0, 0)
        c[1].move(w - size, 0)
        c[2].move(0, h - size)
        c[3].move(w - size, h - size)
        for grip in self._edges.values():
            grip.raise_()
        for grip in self._corners:
            grip.raise_()
