"""List item widget representing a single note as a colored card."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from config.categories import NOTE_TYPE_COLORS
from core.note import Note
from services.theme_service import get_theme_service


class NoteCard(QFrame):
    """노트 유형 색상 힌트를 가진 카드 위젯."""

    def __init__(self, note: Note, parent=None) -> None:
        super().__init__(parent)
        self.note_id = note.id
        self.setObjectName("NoteCard")

        color = note.color_hint or get_theme_service().get_card_color(
            note.note_type) or NOTE_TYPE_COLORS.get(note.note_type, "#777777")
        self.setStyleSheet(
            "#NoteCard { border-left: 5px solid %s; border-radius: 4px;"
            " background-color: rgba(255,255,255,0.04); }" % color
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)

        body = QVBoxLayout()
        title = note.title or "제목 없음"
        if note.is_pinned:
            title = "📌 " + title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        body.addWidget(title_label)

        preview_text = (note.body or "").strip().replace("\n", " ")
        if len(preview_text) > 60:
            preview_text = preview_text[:60] + "…"
        preview = QLabel(preview_text)
        preview.setStyleSheet("color: #aaaaaa;")
        body.addWidget(preview)
        outer.addLayout(body, 1)

        type_label = QLabel(note.note_type)
        type_label.setAlignment(Qt.AlignTop | Qt.AlignRight)
        type_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        outer.addWidget(type_label, 0)
