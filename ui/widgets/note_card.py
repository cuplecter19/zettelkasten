"""List item widget representing a single note as a colored card."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QStyle,
                               QToolButton, QVBoxLayout)

from config.categories import NOTE_TYPE_COLORS
from core.note import Note
from services.theme_service import get_theme_service

# 카드 좌측 썸네일 한 변 크기(px). 카드 높이에 맞춰 48~64px 범위.
THUMBNAIL_SIZE = 56


class NoteCard(QFrame):
    """노트 유형 색상 힌트를 가진 카드 위젯.

    우측 끝에 휴지통 삭제 버튼을 두고, 첨부 이미지가 있으면 좌측에 썸네일을,
    PDF만 있으면 PDF 아이콘을 표시한다.
    """

    delete_requested = Signal(str)

    def __init__(self, note: Note, thumbnail: bytes | None = None,
                 has_pdf: bool = False, parent=None) -> None:
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
        outer.setSpacing(8)

        # 좌측 썸네일/아이콘(첨부가 있을 때만).
        thumb_label = self._build_thumbnail(thumbnail, has_pdf)
        if thumb_label is not None:
            outer.addWidget(thumb_label, 0)

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

        # 우측 끝 삭제 버튼.
        self._delete_btn = QToolButton(self)
        self._delete_btn.setText("🗑")
        self._delete_btn.setToolTip("이 노트를 삭제합니다")
        self._delete_btn.setAutoRaise(True)
        self._delete_btn.setCursor(Qt.PointingHandCursor)
        self._delete_btn.clicked.connect(
            lambda: self.delete_requested.emit(self.note_id))
        outer.addWidget(self._delete_btn, 0, Qt.AlignTop)

    def _build_thumbnail(self, thumbnail: bytes | None,
                         has_pdf: bool) -> QLabel | None:
        """첨부 이미지 썸네일 또는 PDF 아이콘 라벨을 만든다."""
        if thumbnail:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail)
            if not pixmap.isNull():
                label = QLabel(self)
                label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
                label.setScaledContents(True)
                label.setPixmap(pixmap.scaled(
                    QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE),
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                return label
        if has_pdf:
            label = QLabel(self)
            label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            icon = self.style().standardIcon(QStyle.SP_FileIcon)
            label.setPixmap(icon.pixmap(QSize(32, 32)))
            label.setAlignment(Qt.AlignCenter)
            return label
        return None
