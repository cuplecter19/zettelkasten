"""설정 다이얼로그의 패널 모드 탭 — 대시보드 모듈형 패널 토글.

대시보드를 구성하는 패널 모듈(요약·유형별 노트 등)의 표시 여부를
:class:`~services.panel_service.PanelService` 를 통해 켜고 끈다. 변경은 즉시
저장되고 ``panels_changed`` 시그널로 대시보드 탭에 반영된다.

다른 설정 탭과 동일하게 서비스 1개만 의존하는 독립 패널로 구성된다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QLabel, QVBoxLayout, QWidget)

from services.panel_service import DASHBOARD_PANELS, PanelService


class SettingsPanelTab(QWidget):
    """패널 모드 탭: 대시보드 패널 모듈을 켜고 끈다."""

    def __init__(self, panels: PanelService, parent=None) -> None:
        super().__init__(parent)
        self._panels = panels
        self._checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        intro = QLabel(
            "대시보드에 표시할 모듈형 패널을 선택하세요.", self)
        intro.setWordWrap(True)
        root.addWidget(intro)

        for panel, label in DASHBOARD_PANELS.items():
            check = QCheckBox(label, self)
            check.setChecked(self._panels.is_enabled(panel))
            check.toggled.connect(
                lambda checked, p=panel: self._panels.set_enabled(p, checked))
            self._checks[panel] = check
            root.addWidget(check)

        root.addStretch(1)

        # 외부에서 패널 상태가 바뀌면 체크박스를 갱신.
        self._panels.panels_changed.connect(self._sync)

    def _sync(self) -> None:
        for panel, check in self._checks.items():
            check.blockSignals(True)
            check.setChecked(self._panels.is_enabled(panel))
            check.blockSignals(False)


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    from services.panel_service import PanelService

    app = QApplication(sys.argv)
    widget = SettingsPanelTab(PanelService())
    widget.resize(360, 240)
    widget.show()
    sys.exit(app.exec())
