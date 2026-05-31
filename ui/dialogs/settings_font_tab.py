"""설정 다이얼로그의 폰트 탭 — 사용자 폰트 업로드 및 요소별 지정.

사용자가 폰트 파일을 직접 업로드하고, **기본 텍스트** 및 **마크다운 요소별**로
폰트를 지정한다. :class:`~services.font_service.FontService` 를 통해 변경되며,
변경은 즉시 저장되고 ``fonts_changed`` 시그널로 마크다운 미리보기에 반영된다.

다른 설정 탭과 동일하게 서비스 1개만 의존하는 독립 패널로 구성된다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QLabel, QMessageBox, QPushButton, QVBoxLayout,
                               QWidget)

from services.font_service import FONT_TARGETS, FontService

# 폰트 미지정(상속)을 나타내는 콤보박스 항목 라벨과 내부 값.
_DEFAULT_LABEL = "(기본)"
_DEFAULT_VALUE = ""

_FONT_FILTER = "폰트 파일 (*.ttf *.otf *.ttc);;모든 파일 (*)"


class SettingsFontTab(QWidget):
    """폰트 탭: 폰트 업로드 + 대상별 폰트 패밀리 지정."""

    def __init__(self, fonts: FontService, parent=None) -> None:
        super().__init__(parent)
        self._fonts = fonts
        self._combos: dict[str, QComboBox] = {}

        root = QVBoxLayout(self)

        # 상단: 폰트 업로드.
        upload_row = QHBoxLayout()
        upload_btn = QPushButton("폰트 파일 업로드…", self)
        upload_btn.clicked.connect(self._upload_font)
        upload_row.addWidget(upload_btn)
        upload_row.addStretch(1)
        root.addLayout(upload_row)

        # 중단: 대상별 폰트 지정.
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        for col, text in enumerate(["대상", "폰트"]):
            header = QLabel(text, self)
            header.setStyleSheet("font-weight: bold;")
            grid.addWidget(header, 0, col)

        for row, (target, label) in enumerate(FONT_TARGETS.items(), start=1):
            grid.addWidget(QLabel(label, self), row, 0)
            combo = QComboBox(self)
            combo.setMinimumWidth(220)
            self._populate_combo(combo, self._fonts.get_assignment(target))
            combo.currentIndexChanged.connect(
                lambda _idx, t=target: self._on_changed(t))
            grid.addWidget(combo, row, 1)
            self._combos[target] = combo
        root.addLayout(grid)

        # 하단: 기본값 복원.
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        reset_btn = QPushButton("기본값으로 복원", self)
        reset_btn.clicked.connect(self._reset)
        buttons.addWidget(reset_btn)
        root.addLayout(buttons)
        root.addStretch(1)

        # 외부에서 폰트 설정이 바뀌면 콤보박스를 갱신.
        self._fonts.fonts_changed.connect(self._sync)

    # ----- 콤보박스 구성 --------------------------------------------------
    def _populate_combo(self, combo: QComboBox, current: str) -> None:
        """콤보박스를 (기본) + 사용 가능한 폰트 패밀리로 채운다."""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(_DEFAULT_LABEL, _DEFAULT_VALUE)
        for family in self._fonts.available_families():
            combo.addItem(family, family)
        index = combo.findData(current or _DEFAULT_VALUE)
        if index < 0 and current:
            # 등록되지 않은 패밀리도 선택 상태를 보존한다.
            combo.addItem(current, current)
            index = combo.count() - 1
        combo.setCurrentIndex(max(index, 0))
        combo.blockSignals(False)

    def _on_changed(self, target: str) -> None:
        combo = self._combos[target]
        self._fonts.set_assignment(target, combo.currentData() or "")

    def _upload_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "업로드할 폰트 파일 선택", "", _FONT_FILTER)
        if not path:
            return
        family = self._fonts.add_font_file(path)
        if family is None:
            QMessageBox.warning(
                self, "오류", "폰트 파일을 등록하지 못했습니다.")

    def _reset(self) -> None:
        self._fonts.reset()
        self._sync()

    def _sync(self) -> None:
        for target, combo in self._combos.items():
            self._populate_combo(combo, self._fonts.get_assignment(target))


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    from services.font_service import FontService

    app = QApplication(sys.argv)
    widget = SettingsFontTab(FontService())
    widget.resize(480, 360)
    widget.show()
    sys.exit(app.exec())
