"""Phase 4 — 설정 다이얼로그의 마크다운 탭.

마크다운 미리보기 요소별 서식(글꼴 크기·색상·굵기·기울임)을
:class:`~services.markdown_style_service.MarkdownStyleService` 를 통해 변경한다.
변경은 즉시 저장되고 ``style_changed`` 시그널로 미리보기에 반영된다.

다른 설정 탭(:mod:`ui.dialogs.settings_design_tab`,
:mod:`ui.dialogs.settings_css_tab`)과 동일하게 서비스 1개만 의존하는 독립 패널로
구성되어, 후속 Phase(대시보드)의 추가와 충돌하지 않는다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from services.markdown_style_service import (MARKDOWN_ELEMENTS,
                                             MarkdownStyleService)


class _ColorSwatch(QPushButton):
    """현재 색상을 표시하고 클릭 시 색상 선택기를 여는 버튼."""

    def __init__(self, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(90, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self._color = color
        self.setText(color)
        self.setStyleSheet(
            f"background-color: {color}; color: {_contrast(color)};"
            " border: 1px solid #555; border-radius: 4px;")

    @property
    def color(self) -> str:
        return self._color


def _contrast(hex_color: str) -> str:
    """배경 대비 가독성을 위해 검정/흰색 텍스트 색을 고른다."""
    c = QColor(hex_color)
    luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
    return "#000000" if luminance > 140 else "#ffffff"


class SettingsMarkdownTab(QWidget):
    """마크다운 탭: 요소별 글꼴 크기/색상/굵기/기울임을 지정한다."""

    def __init__(self, style: MarkdownStyleService, parent=None) -> None:
        super().__init__(parent)
        self._style = style
        # 요소별 위젯 묶음: {element: {"size", "swatch", "bold", "italic"}}.
        self._rows: dict[str, dict] = {}

        root = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        headers = ["요소", "크기", "색상", "굵게", "기울임"]
        for col, text in enumerate(headers):
            header = QLabel(text, self)
            header.setStyleSheet("font-weight: bold;")
            grid.addWidget(header, 0, col)

        for row, (element, label) in enumerate(MARKDOWN_ELEMENTS.items(), start=1):
            current = self._style.get_style(element)
            grid.addWidget(QLabel(label, self), row, 0)

            size = QSpinBox(self)
            size.setRange(8, 72)
            size.setSuffix(" px")
            size.setValue(int(current.get("font_size", 14)))
            size.valueChanged.connect(
                lambda value, el=element: self._style.set_field(el, "font_size", value))
            grid.addWidget(size, row, 1)

            swatch = _ColorSwatch(current.get("color", "#e0e0e0"), self)
            swatch.clicked.connect(lambda _checked=False, el=element: self._pick(el))
            grid.addWidget(swatch, row, 2)

            bold = QCheckBox(self)
            bold.setChecked(bool(current.get("bold")))
            bold.toggled.connect(
                lambda checked, el=element: self._style.set_field(el, "bold", checked))
            grid.addWidget(bold, row, 3, alignment=Qt.AlignCenter)

            italic = QCheckBox(self)
            italic.setChecked(bool(current.get("italic")))
            italic.toggled.connect(
                lambda checked, el=element: self._style.set_field(el, "italic", checked))
            grid.addWidget(italic, row, 4, alignment=Qt.AlignCenter)

            self._rows[element] = {
                "size": size, "swatch": swatch, "bold": bold, "italic": italic}

        root.addLayout(grid)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        reset_btn = QPushButton("기본값으로 복원", self)
        reset_btn.clicked.connect(self._reset)
        buttons.addWidget(reset_btn)
        root.addLayout(buttons)
        root.addStretch(1)

        # 외부에서 서식이 바뀌면 위젯을 갱신.
        self._style.style_changed.connect(self._sync)

    def _pick(self, element: str) -> None:
        current = QColor(self._style.get_style(element).get("color", "#e0e0e0"))
        color = QColorDialog.getColor(
            current, self, MARKDOWN_ELEMENTS.get(element, element))
        if color.isValid():
            self._style.set_field(element, "color", color.name())
            self._rows[element]["swatch"].set_color(color.name())

    def _reset(self) -> None:
        self._style.reset()
        self._sync()

    def _sync(self) -> None:
        for element, widgets in self._rows.items():
            style = self._style.get_style(element)
            widgets["size"].blockSignals(True)
            widgets["size"].setValue(int(style.get("font_size", 14)))
            widgets["size"].blockSignals(False)
            widgets["swatch"].set_color(style.get("color", "#e0e0e0"))
            widgets["bold"].blockSignals(True)
            widgets["bold"].setChecked(bool(style.get("bold")))
            widgets["bold"].blockSignals(False)
            widgets["italic"].blockSignals(True)
            widgets["italic"].setChecked(bool(style.get("italic")))
            widgets["italic"].blockSignals(False)


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    from services.markdown_style_service import MarkdownStyleService

    app = QApplication(sys.argv)
    widget = SettingsMarkdownTab(MarkdownStyleService())
    widget.resize(480, 360)
    widget.show()
    sys.exit(app.exec())
