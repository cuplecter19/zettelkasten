"""앱 시작 시 보여주는 무압박 첫 화면 오버레이."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QLabel, QVBoxLayout,
                               QWidget)


class StartupDashboardOverlay(QWidget):
    """색상 또는 이미지로 채운 뒤 클릭하면 서서히 사라지는 오버레이."""

    def __init__(self, color: str, image_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StartupDashboardOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._color = color or "#f5ead7"
        self._image_path = image_path or ""
        self._pixmap = QPixmap(self._image_path) if self._image_path else QPixmap()

        self._image = QLabel(self)
        self._image.setObjectName("StartupDashboardImage")
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setScaledContents(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.addStretch(1)
        self._message = QLabel("오늘도 천천히 시작해도 괜찮아요", self)
        self._message.setObjectName("StartupDashboardMessage")
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setStyleSheet(
            "font-size: 24px; font-weight: 600;"
            "background-color: rgba(255, 255, 255, 140);"
            "border-radius: 18px; padding: 18px 28px;")
        layout.addWidget(self._message, 0, Qt.AlignCenter)
        layout.addStretch(1)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(900)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.finished.connect(self.hide)

        self._apply_background()

    def _apply_background(self) -> None:
        self.setStyleSheet(f"""
        QWidget#StartupDashboardOverlay {{
            background-color: {self._color};
        }}
        """)
        if not self._pixmap.isNull() and Path(self._image_path).exists():
            self._image.show()
            self._update_pixmap()
        else:
            self._image.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._image.setGeometry(self.rect())
        self._update_pixmap()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.fade_out()
            event.accept()
            return
        super().mousePressEvent(event)

    def fade_out(self) -> None:
        """오버레이를 페이드아웃한다."""
        if self._animation.state() == QAbstractAnimation.Running:
            return
        self._animation.start()

    def _update_pixmap(self) -> None:
        if self._pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._image.setPixmap(scaled)
