"""설정 다이얼로그.

좌측 카테고리 목록(``QListWidget``)과 우측 카테고리별 내용
(``QStackedWidget``)으로 구성된다. 카테고리는 **디자인 / 마크다운 / CSS 스니펫 /
대시보드** 이며, 각 탭은 자신의 서비스 하나에만 의존하는 독립 패널이다.

탭은 :meth:`SettingsDialog._build_pages` 의 모듈형 레지스트리로 등록되므로, 각
탭은 자신의 서비스 하나만 교체/추가하면 되고 다른 탭과 충돌하지 않는다. 아직
구현되지 않은 카테고리가 있으면 빈 플레이스홀더로 둔다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget,
                               QStackedWidget, QVBoxLayout, QWidget)

from services.css_snippet_service import (CssSnippetService,
                                          get_css_snippet_service)
from services.dashboard_service import (DashboardService,
                                        get_dashboard_service)
from services.font_service import FontService, get_font_service
from services.markdown_style_service import (MarkdownStyleService,
                                             get_markdown_style_service)
from services.panel_service import PanelService, get_panel_service
from services.theme_service import ThemeService, get_theme_service
from ui.dialogs.settings_css_tab import SettingsCssTab
from ui.dialogs.settings_dashboard_tab import SettingsDashboardTab
from ui.dialogs.settings_design_tab import SettingsDesignTab
from ui.dialogs.settings_font_tab import SettingsFontTab
from ui.dialogs.settings_markdown_tab import SettingsMarkdownTab
from ui.dialogs.settings_panel_tab import SettingsPanelTab

# 카테고리 순서(목록과 스택 인덱스가 일치한다).
CATEGORIES = ["디자인", "마크다운", "CSS 스니펫", "대시보드", "폰트", "패널 모드"]


def _placeholder(text: str) -> QWidget:
    """후속 Phase 에서 채울 빈 탭 플레이스홀더."""
    page = QWidget()
    page.setObjectName("SettingsPage")
    layout = QVBoxLayout(page)
    label = QLabel(f"{text} 설정은 곧 제공됩니다.")
    label.setEnabled(False)
    layout.addWidget(label)
    layout.addStretch(1)
    return page


class SettingsDialog(QDialog):
    """카테고리 기반 설정 다이얼로그."""

    def __init__(self, parent=None, theme: ThemeService | None = None,
                 markdown_style: MarkdownStyleService | None = None,
                 css_snippets: CssSnippetService | None = None,
                 dashboard: DashboardService | None = None,
                 fonts: FontService | None = None,
                 panels: PanelService | None = None) -> None:
        super().__init__(parent)
        self._theme = theme or get_theme_service()
        self._markdown_style = markdown_style or get_markdown_style_service()
        self._css_snippets = css_snippets or get_css_snippet_service()
        self._dashboard = dashboard or get_dashboard_service()
        self._fonts = fonts or get_font_service()
        self._panels = panels or get_panel_service()
        self.setWindowTitle("설정")
        self.setObjectName("SettingsDialog")
        self.resize(720, 520)

        layout = QHBoxLayout(self)

        self._list = QListWidget(self)
        self._list.setObjectName("SettingsCategoryList")
        self._list.setFixedWidth(160)
        self._list.addItems(CATEGORIES)
        self._list.currentRowChanged.connect(self._on_category_changed)
        layout.addWidget(self._list)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("SettingsStack")
        layout.addWidget(self._stack, 1)

        for page in self._build_pages():
            self._stack.addWidget(page)

        self._list.setCurrentRow(0)

    def _build_pages(self) -> list[QWidget]:
        """카테고리 순서에 맞춰 탭 패널을 생성한다(모듈형 레지스트리).

        구현된 탭은 자신의 서비스만 받는 독립 패널이며, 미구현 카테고리는
        플레이스홀더로 채운다.
        """
        self._design_tab = SettingsDesignTab(self._theme, self)
        self._design_tab.setObjectName("SettingsPage")
        self._markdown_tab = SettingsMarkdownTab(self._markdown_style, self)
        self._markdown_tab.setObjectName("SettingsPage")
        self._css_tab = SettingsCssTab(self._css_snippets, self)
        self._css_tab.setObjectName("SettingsPage")
        self._dashboard_tab = SettingsDashboardTab(
            self._dashboard, self, panels=self._panels)
        self._dashboard_tab.setObjectName("SettingsPage")
        self._font_tab = SettingsFontTab(self._fonts, self)
        self._font_tab.setObjectName("SettingsPage")
        self._panel_tab = SettingsPanelTab(self._panels, self)
        self._panel_tab.setObjectName("SettingsPage")
        return [
            self._design_tab,              # 디자인 (Phase 1-3)
            self._markdown_tab,            # 마크다운 (Phase 4)
            self._css_tab,                 # CSS 스니펫 (Phase 5)
            self._dashboard_tab,           # 대시보드 (Phase 6)
            self._font_tab,                # 폰트 (사용자 폰트 업로드/지정)
            self._panel_tab,               # 패널 모드 (모듈형 대시보드 패널)
        ]

    def _on_category_changed(self, row: int) -> None:
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)
            # 대시보드 탭으로 전환할 때 최신 통계를 다시 읽는다.
            if self._stack.widget(row) is self._dashboard_tab:
                self._dashboard_tab.refresh()
