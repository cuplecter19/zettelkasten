"""설정 다이얼로그.

좌측 카테고리 목록(``QListWidget``)과 우측 카테고리별 내용
(``QStackedWidget``)으로 구성된다. 초기 카테고리는 **디자인 / 마크다운 /
CSS 스니펫 / 대시보드** 이며, 디자인 탭만 이번 Phase 에서 구현하고 나머지는
후속 Phase 에서 채울 빈 플레이스홀더로 둔다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget,
                               QStackedWidget, QVBoxLayout, QWidget)

from services.theme_service import ThemeService, get_theme_service
from ui.dialogs.settings_design_tab import SettingsDesignTab

# 카테고리 순서(목록과 스택 인덱스가 일치한다).
CATEGORIES = ["디자인", "마크다운", "CSS 스니펫", "대시보드"]


def _placeholder(text: str) -> QWidget:
    """후속 Phase 에서 채울 빈 탭 플레이스홀더."""
    page = QWidget()
    layout = QVBoxLayout(page)
    label = QLabel(f"{text} 설정은 곧 제공됩니다.")
    label.setEnabled(False)
    layout.addWidget(label)
    layout.addStretch(1)
    return page


class SettingsDialog(QDialog):
    """카테고리 기반 설정 다이얼로그."""

    def __init__(self, parent=None, theme: ThemeService | None = None) -> None:
        super().__init__(parent)
        self._theme = theme or get_theme_service()
        self.setWindowTitle("설정")
        self.resize(640, 480)

        layout = QHBoxLayout(self)

        self._list = QListWidget(self)
        self._list.setFixedWidth(160)
        self._list.addItems(CATEGORIES)
        self._list.currentRowChanged.connect(self._on_category_changed)
        layout.addWidget(self._list)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack, 1)

        # 디자인 탭(구현됨) + 나머지 플레이스홀더.
        self._design_tab = SettingsDesignTab(self._theme, self)
        self._stack.addWidget(self._design_tab)
        for name in CATEGORIES[1:]:
            self._stack.addWidget(_placeholder(name))

        self._list.setCurrentRow(0)

    def _on_category_changed(self, row: int) -> None:
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)
