"""Editor panel: title, body, auto-save, type suggestion banner and tags."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
                               QWidget)

from config.categories import NOTE_TYPE_COLORS
from core.note import Note
from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository
from services.classifier import NoteClassifier
from ui.widgets.tag_chip import TagChip

logger = logging.getLogger(__name__)


class EditorPanel(QWidget):
    """포커스 이탈 시 자동 저장되는 노트 편집 패널."""

    note_saved = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = NoteRepository()
        self._tag_repo = TagRepository()
        self._classifier = NoteClassifier()
        self._current_id: str | None = None
        self._suggested_type: str | None = None

        layout = QVBoxLayout(self)

        self._title = QLineEdit(self)
        self._title.setPlaceholderText("제목")
        self._title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._title)

        # 자동 분류 제안 배너.
        self._banner = QFrame(self)
        self._banner.setVisible(False)
        banner_layout = QHBoxLayout(self._banner)
        banner_layout.setContentsMargins(8, 4, 8, 4)
        self._banner_label = QLabel("", self._banner)
        banner_layout.addWidget(self._banner_label, 1)
        self._apply_btn = QPushButton("적용", self._banner)
        self._ignore_btn = QPushButton("무시", self._banner)
        banner_layout.addWidget(self._apply_btn)
        banner_layout.addWidget(self._ignore_btn)
        self._apply_btn.clicked.connect(self._apply_suggestion)
        self._ignore_btn.clicked.connect(lambda: self._banner.setVisible(False))
        layout.addWidget(self._banner)

        self._body = QTextEdit(self)
        self._body.setPlaceholderText("본문을 입력하세요. 포커스를 벗어나면 자동 저장됩니다.")
        layout.addWidget(self._body, 1)

        # 태그 칩 영역.
        self._tags_container = QWidget(self)
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.addStretch(1)
        layout.addWidget(self._tags_container)

        # 자동 저장을 위한 포커스 감시.
        self._title.installEventFilter(self)
        self._body.installEventFilter(self)
        self.setEnabled(False)

    # ----- 노트 로딩/저장 -------------------------------------------------
    def load_note(self, note: Note | None) -> None:
        self._current_id = note.id if note else None
        self.setEnabled(note is not None)
        if note is None:
            self._title.clear()
            self._body.clear()
            self._banner.setVisible(False)
            return
        self._title.setText(note.title)
        self._body.setPlainText(note.body)
        self._refresh_tags()
        self._update_suggestion_banner()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt naming)
        if event.type() == QEvent.FocusOut and self._current_id is not None:
            self._save()
        return super().eventFilter(obj, event)

    def _save(self) -> None:
        if self._current_id is None:
            return
        try:
            self._repo.update(
                self._current_id,
                title=self._title.text().strip() or "제목 없음",
                body=self._body.toPlainText(),
            )
            self.note_saved.emit(self._current_id)
            self._update_suggestion_banner()
        except Exception:
            logger.exception("Auto-save failed")
            QMessageBox.warning(self, "오류", "노트를 저장하지 못했습니다.")

    # ----- 분류 제안 ------------------------------------------------------
    def _update_suggestion_banner(self) -> None:
        if self._current_id is None:
            return
        note = self._repo.get_by_id(self._current_id)
        if note is None:
            return
        suggested = self._classifier.suggest_type(
            self._title.text(), self._body.toPlainText())
        if suggested != note.note_type:
            self._suggested_type = suggested
            self._banner_label.setText(
                f"이 노트를 [{suggested}]으로 분류할까요?")
            self._banner.setVisible(True)
        else:
            self._banner.setVisible(False)

    def _apply_suggestion(self) -> None:
        if self._current_id is None or self._suggested_type is None:
            return
        try:
            color = NOTE_TYPE_COLORS.get(self._suggested_type)
            self._repo.update(self._current_id,
                              note_type=self._suggested_type,
                              color_hint=color)
            self._banner.setVisible(False)
            self.note_saved.emit(self._current_id)
        except Exception:
            logger.exception("Failed to apply type suggestion")

    # ----- 태그 ----------------------------------------------------------
    def _refresh_tags(self) -> None:
        # 기존 칩 제거(마지막 stretch 제외).
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if self._current_id is None:
            return
        for tag in self._tag_repo.get_tags_for_note(self._current_id):
            chip = TagChip(tag.name, color=tag.color, removable=True)
            chip.removed.connect(self._on_tag_removed)
            self._tags_layout.insertWidget(self._tags_layout.count() - 1, chip)

    def _on_tag_removed(self, name: str) -> None:
        if self._current_id is None:
            return
        tag = self._tag_repo.get_by_name(name)
        if tag is not None:
            self._tag_repo.remove_tag_from_note(self._current_id, tag.id)
        self._refresh_tags()
