"""연결되지 않은 노트 목록 다이얼로그."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout)

from core.note import Note


class OrphanNotesDialog(QDialog):
    """아직 링크가 없는 노트를 보여주는 주간 수집 창."""

    note_requested = Signal(str)

    def __init__(self, notes: list[Note], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("아직 연결되지 않은 아이디어들")
        self.setObjectName("OrphanNotesDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
        QDialog#OrphanNotesDialog {
            background-color: #fff7e8;
            color: #3a3f47;
        }
        QDialog#OrphanNotesDialog QListWidget {
            background-color: #fffdf8;
            border: none;
            border-radius: 12px;
            padding: 8px;
        }
        """)
        self.resize(460, 520)

        layout = QVBoxLayout(self)
        title = QLabel("아직 연결되지 않은 아이디어들", self)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        guide = QLabel(
            "어딘가에 이어질 수 있는 노트들을 모았습니다. "
            "천천히 열어보고 기존 메모와 연결해 보세요.",
            self,
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)

        self._list = QListWidget(self)
        self._list.itemClicked.connect(self._on_item_clicked)
        for note in notes:
            item = QListWidgetItem(f"{note.title}  ({note.note_type})")
            item.setData(Qt.UserRole, note.id)
            self._list.addItem(item)
        layout.addWidget(self._list, 1)

        close_btn = QPushButton("닫기", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignRight)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(Qt.UserRole)
        if note_id:
            self.note_requested.emit(note_id)
