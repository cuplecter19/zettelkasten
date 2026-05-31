"""Explorer panel: filterable, searchable note list with colored cards."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from db.repositories.note_repo import NoteRepository
from services.search_service import SearchService
from ui.widgets.note_card import NoteCard

logger = logging.getLogger(__name__)

_FILTERS = ["전체", "LEARNING", "IDEA", "MOOD", "ARCHIVE"]


class ExplorerPanel(QWidget):
    """유형 필터와 검색을 지원하는 노트 목록 패널."""

    note_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = NoteRepository()
        self._search = SearchService()
        self._query = ""
        self._active_type: str | None = None

        layout = QVBoxLayout(self)

        # 유형별 필터 버튼.
        filter_bar = QHBoxLayout()
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        for label in _FILTERS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            if label == "전체":
                btn.setChecked(True)
            btn.clicked.connect(lambda _checked, lbl=label: self._on_filter(lbl))
            self._button_group.addButton(btn)
            filter_bar.addWidget(btn)
        layout.addLayout(filter_bar)

        self._list = QListWidget(self)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

        self.refresh()

    # ----- 외부 API -------------------------------------------------------
    def set_query(self, query: str) -> None:
        self._query = query or ""
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        notes = self._collect_notes()
        for note in notes:
            card = NoteCard(note)
            item = QListWidgetItem(self._list)
            item.setSizeHint(QSize(0, max(card.sizeHint().height(), 56)))
            item.setData(256, note.id)  # Qt.UserRole
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def select_note(self, note_id: str) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(256) == note_id:
                self._list.setCurrentItem(item)
                break

    # ----- 내부 --------------------------------------------------------
    def _collect_notes(self):
        if self._query.strip():
            notes = self._search.combined_search(
                self._query, note_type=self._active_type)
        elif self._active_type:
            notes = self._repo.get_by_type(self._active_type)
        else:
            notes = self._repo.list_all()
        return notes

    def _on_filter(self, label: str) -> None:
        self._active_type = None if label == "전체" else label
        self.refresh()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(256)
        if note_id:
            self.note_selected.emit(note_id)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    widget = ExplorerPanel()
    widget.resize(400, 700)
    widget.show()
    sys.exit(app.exec())
