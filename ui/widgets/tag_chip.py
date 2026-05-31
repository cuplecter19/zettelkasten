"""Small pill-shaped tag chip widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton


class TagChip(QFrame):
    """이름과 선택적 삭제 버튼을 가진 태그 칩."""

    removed = Signal(str)

    def __init__(self, name: str, color: str | None = None,
                 removable: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._name = name
        self.setObjectName("TagChip")

        bg = color or "#555555"
        self.setStyleSheet(
            f"#TagChip {{ background-color: {bg}; border-radius: 8px; }}"
            "QLabel { color: white; padding: 2px 4px; }"
            "QToolButton { color: white; border: none; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(2)

        layout.addWidget(QLabel(f"#{name}"))

        if removable:
            btn = QToolButton(self)
            btn.setText("×")
            btn.clicked.connect(lambda: self.removed.emit(self._name))
            layout.addWidget(btn)

    @property
    def name(self) -> str:
        return self._name
