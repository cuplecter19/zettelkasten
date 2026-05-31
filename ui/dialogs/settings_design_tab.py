"""설정 다이얼로그의 디자인 탭 — UI 색상 커스터마이징.

각 UI 요소의 색상을 :class:`~services.theme_service.ThemeService` 를 통해
변경한다. 색상 선택은 ``QColorDialog`` 로 수행하며, 변경 즉시 전역 스타일에
반영되어 실시간 미리보기가 가능하다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFormLayout, QHBoxLayout,
                               QPushButton, QVBoxLayout, QWidget)

from services.theme_service import THEME_LABELS, ThemeService


class _ColorSwatch(QPushButton):
    """현재 색상을 표시하고 클릭 시 색상 선택기를 여는 버튼."""

    def __init__(self, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(120, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self._color = color
        # 강제 색상이므로 전역 QSS 영향을 받지 않도록 인라인 스타일로 지정.
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


class SettingsDesignTab(QWidget):
    """디자인 탭: 각 UI 요소의 색상을 지정한다."""

    def __init__(self, theme: ThemeService, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._swatches: dict[str, _ColorSwatch] = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        for key, label in THEME_LABELS.items():
            swatch = _ColorSwatch(theme.get_color(key), self)
            swatch.clicked.connect(lambda _checked=False, k=key: self._pick(k))
            self._swatches[key] = swatch
            form.addRow(label, swatch)
        root.addLayout(form)

        # 기본값 복원 버튼.
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        reset_btn = QPushButton("기본값으로 복원", self)
        reset_btn.clicked.connect(self._reset)
        buttons.addWidget(reset_btn)
        root.addLayout(buttons)
        root.addStretch(1)

        # 외부에서 테마가 바뀌면 스와치를 갱신.
        self._theme.theme_changed.connect(self._sync_swatches)

    def _pick(self, key: str) -> None:
        current = QColor(self._theme.get_color(key))
        color = QColorDialog.getColor(current, self, THEME_LABELS.get(key, key))
        if color.isValid():
            self._theme.set_color(key, color.name())
            self._swatches[key].set_color(color.name())

    def _reset(self) -> None:
        self._theme.reset()
        self._sync_swatches()

    def _sync_swatches(self) -> None:
        for key, swatch in self._swatches.items():
            swatch.set_color(self._theme.get_color(key))
