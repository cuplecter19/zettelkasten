"""Phase 6 — 설정 다이얼로그의 대시보드 탭.

로컬 지식 베이스의 요약 통계(노트 수, 유형별 분포, 태그/링크/첨부 수 등)를
:class:`~services.dashboard_service.DashboardService` 로부터 읽어 표시한다.

다른 설정 탭(:mod:`ui.dialogs.settings_design_tab`,
:mod:`ui.dialogs.settings_markdown_tab`, :mod:`ui.dialogs.settings_css_tab`)과
동일하게 서비스 1개만 의존하는 독립 패널로 구성되어, 기존 기능과 충돌하지 않는다.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QFrame, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from services.dashboard_service import NOTE_TYPE_LABELS, DashboardService
from services.panel_service import PanelService, get_panel_service


class SettingsDashboardTab(QWidget):
    """대시보드 탭: 지식 베이스 통계를 요약해 보여준다.

    표시되는 패널은 :class:`~services.panel_service.PanelService`(패널 모드)에
    따라 모듈 단위로 켜고 끌 수 있다.
    """

    def __init__(self, dashboard: DashboardService, parent=None,
                 panels: PanelService | None = None) -> None:
        super().__init__(parent)
        self._dashboard = dashboard
        self._panels = panels or get_panel_service()
        self._values: dict[str, QLabel] = {}
        # 패널 키 → 패널 위젯(패널 모드 표시/숨김 대상).
        self._panel_widgets: dict[str, QWidget] = {}

        root = QVBoxLayout(self)

        welcome = QGroupBox("첫 화면", self)
        welcome_layout = QVBoxLayout(welcome)
        welcome_guide = QLabel(
            "프로그램을 켰을 때 보이는 무압박 대시보드의 색상 또는 이미지를 "
            "설정합니다. 이미지를 지정하면 색상 위에 이미지가 표시됩니다.",
            self,
        )
        welcome_guide.setWordWrap(True)
        welcome_layout.addWidget(welcome_guide)

        welcome_buttons = QHBoxLayout()
        self._welcome_color_btn = QPushButton(self)
        self._welcome_color_btn.clicked.connect(self._pick_welcome_color)
        welcome_buttons.addWidget(self._welcome_color_btn)
        image_btn = QPushButton("이미지 선택…", self)
        image_btn.clicked.connect(self._pick_welcome_image)
        welcome_buttons.addWidget(image_btn)
        clear_image_btn = QPushButton("이미지 제거", self)
        clear_image_btn.clicked.connect(self._clear_welcome_image)
        welcome_buttons.addWidget(clear_image_btn)
        welcome_buttons.addStretch(1)
        welcome_layout.addLayout(welcome_buttons)

        self._welcome_image_label = QLabel(self)
        self._welcome_image_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        welcome_layout.addWidget(self._welcome_image_label)
        root.addWidget(welcome)

        # 상단: 핵심 요약 카드.
        summary = QGroupBox("요약", self)
        summary_grid = QGridLayout(summary)
        summary_grid.setHorizontalSpacing(16)
        summary_grid.setVerticalSpacing(6)
        self._add_metric(summary_grid, 0, "total_notes", "전체 노트")
        self._add_metric(summary_grid, 1, "pinned_notes", "고정 노트")
        self._add_metric(summary_grid, 2, "untagged_notes", "태그 없는 노트")
        self._add_metric(summary_grid, 3, "total_tags", "태그")
        self._add_metric(summary_grid, 4, "total_links", "노트 링크")
        self._add_metric(summary_grid, 5, "total_attachments", "첨부")
        self._add_metric(summary_grid, 6, "total_pdf_assets", "PDF 자산")
        root.addWidget(summary)
        self._panel_widgets["summary"] = summary

        # 중단: 유형별 노트 분포.
        by_type = QGroupBox("유형별 노트", self)
        type_grid = QGridLayout(by_type)
        type_grid.setHorizontalSpacing(16)
        type_grid.setVerticalSpacing(6)
        for row, (note_type, label) in enumerate(NOTE_TYPE_LABELS.items()):
            self._add_metric(type_grid, row, f"type:{note_type}", label)
        root.addWidget(by_type)
        self._panel_widgets["by_type"] = by_type

        # 하단: 새로고침 버튼.
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        refresh_btn = QPushButton("새로고침", self)
        refresh_btn.clicked.connect(self.refresh)
        buttons.addWidget(refresh_btn)
        root.addLayout(buttons)
        root.addStretch(1)

        # 패널 모드 변경 시 표시/숨김을 갱신.
        self._panels.panels_changed.connect(self._apply_panel_visibility)
        self._dashboard.settings_changed.connect(self._sync_welcome_controls)
        self._apply_panel_visibility()
        self._sync_welcome_controls()
        self.refresh()

    def _add_metric(self, grid: QGridLayout, row: int, key: str,
                    label: str) -> None:
        """라벨-값 한 쌍을 그리드에 추가하고 값 라벨을 등록한다."""
        name = QLabel(label, self)
        value = QLabel("0", self)
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setStyleSheet("font-weight: bold;")
        value.setFrameShape(QFrame.NoFrame)
        grid.addWidget(name, row, 0)
        grid.addWidget(value, row, 1)
        self._values[key] = value

    def _apply_panel_visibility(self) -> None:
        """패널 모드 설정에 따라 각 패널의 표시/숨김을 적용한다."""
        for panel, widget in self._panel_widgets.items():
            widget.setVisible(self._panels.is_enabled(panel))

    def refresh(self) -> None:
        """서비스에서 통계를 다시 읽어 화면을 갱신한다."""
        stats = self._dashboard.collect_stats()
        by_type = stats.get("by_type", {})
        for key, label in self._values.items():
            if key.startswith("type:"):
                label.setText(str(by_type.get(key[len("type:"):], 0)))
            else:
                label.setText(str(stats.get(key, 0)))

    def _pick_welcome_color(self) -> None:
        current = QColor(self._dashboard.welcome_color())
        color = QColorDialog.getColor(current, self, "첫 화면 색상")
        if color.isValid():
            self._dashboard.set_welcome_color(color.name())
            self._sync_welcome_controls()

    def _pick_welcome_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "첫 화면 이미지 선택", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self._dashboard.set_welcome_image_path(path)
            self._sync_welcome_controls()

    def _clear_welcome_image(self) -> None:
        self._dashboard.set_welcome_image_path("")
        self._sync_welcome_controls()

    def _sync_welcome_controls(self) -> None:
        color = self._dashboard.welcome_color()
        qcolor = QColor(color)
        text_color = "#000000" if qcolor.lightness() > 140 else "#ffffff"
        self._welcome_color_btn.setText(f"색상: {color}")
        self._welcome_color_btn.setStyleSheet(
            f"background-color: {color}; color: {text_color};"
            "border: 1px solid #555; border-radius: 4px;")
        image_path = self._dashboard.welcome_image_path()
        if image_path:
            self._welcome_image_label.setText(
                f"이미지: {Path(image_path).name}\n{image_path}")
        else:
            self._welcome_image_label.setText("이미지: 설정 안 함")


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    from db.database import init_db
    from services.dashboard_service import DashboardService

    init_db()
    app = QApplication(sys.argv)
    widget = SettingsDashboardTab(DashboardService())
    widget.resize(420, 420)
    widget.show()
    sys.exit(app.exec())
