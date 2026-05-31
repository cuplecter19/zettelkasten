"""Quick-capture popup dialog and global hotkey manager.

The dialog is a frameless tool window for instant note capture. A global hotkey
(default ``Ctrl+Shift+N``) is registered via the ``keyboard`` library, which
runs its callback on a background thread; the press is forwarded to the Qt main
thread through a queued signal.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QDialog, QLabel, QMessageBox, QPlainTextEdit,
                               QVBoxLayout)

from config.settings import QUICK_CAPTURE_HOTKEY
from db.repositories.note_repo import NoteRepository
from services.classifier import NoteClassifier

logger = logging.getLogger(__name__)


class QuickCaptureDialog(QDialog):
    """Enter 저장 / Esc 취소가 가능한 빠른 메모 팝업."""

    note_saved = Signal(str)  # 새로 저장된 노트 id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = NoteRepository()
        self._classifier = NoteClassifier()

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowTitle("빠른 메모")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("빠른 메모  (Enter 저장 · Esc 취소)"))

        self._editor = QPlainTextEdit(self)
        self._editor.setPlaceholderText("지금 떠오른 생각을 적어보세요…")
        layout.addWidget(self._editor)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        key = event.key()
        # Enter(메인) 또는 키패드 Enter 로 저장. Shift+Enter 는 줄바꿈.
        if key in (Qt.Key_Return, Qt.Key_Enter) and not (
                event.modifiers() & Qt.ShiftModifier):
            self._save()
            return
        if key == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def _save(self) -> None:
        text = self._editor.toPlainText().strip()
        if not text:
            self.reject()
            return
        try:
            first_line = text.splitlines()[0]
            title = first_line[:40] if first_line else "제목 없음"
            note_type = self._classifier.suggest_type(title, text)
            note = self._repo.create(title=title, body=text, note_type=note_type)
            self.note_saved.emit(note.id)
            self._editor.clear()
            self.accept()
        except Exception:
            logger.exception("Quick capture save failed")
            QMessageBox.warning(self, "오류", "메모를 저장하지 못했습니다.")

    def open_fresh(self) -> None:
        """팝업을 비우고 화면 중앙 전면에 표시한다."""
        self._editor.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self._editor.setFocus()


class HotkeyManager(QObject):
    """``keyboard`` 전역 단축키를 Qt 시그널로 중계한다."""

    triggered = Signal()

    def __init__(self, hotkey: str = QUICK_CAPTURE_HOTKEY, parent=None) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._registered = False

    def start(self) -> bool:
        """전역 단축키를 등록한다. 실패해도 앱은 계속 동작한다."""
        try:
            import keyboard
            keyboard.add_hotkey(self._hotkey,
                                lambda: self.triggered.emit())
            self._registered = True
            logger.info("Global hotkey registered: %s", self._hotkey)
        except Exception:
            # 권한 부족(리눅스 root 필요 등)이나 미지원 환경에서 흔히 실패.
            logger.warning("Could not register global hotkey %s", self._hotkey,
                           exc_info=True)
        return self._registered

    def stop(self) -> None:
        if not self._registered:
            return
        try:
            import keyboard
            keyboard.remove_hotkey(self._hotkey)
        except Exception:
            logger.debug("Failed to remove hotkey", exc_info=True)
        self._registered = False


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = QuickCaptureDialog()
    dialog.show()
    sys.exit(app.exec())
