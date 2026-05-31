"""Explorer panel: filterable, searchable note list with colored cards."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QHBoxLayout,
                               QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from config.categories import NOTE_TYPE_COLORS
from db.repositories.attachment_repo import AttachmentRepository
from db.repositories.note_repo import NoteRepository
from services.search_service import SearchService
from ui.widgets.note_card import NoteCard

logger = logging.getLogger(__name__)

_FILTERS = ["전체", "LEARNING", "IDEA", "MOOD", "ARCHIVE"]


class SmoothScrollListWidget(QListWidget):
    """휠 스크롤을 짧은 애니메이션으로 부드럽게 처리하는 목록."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._scroll_animation = QPropertyAnimation(
            self.verticalScrollBar(), b"value", self)
        self._scroll_animation.setDuration(180)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        delta = event.pixelDelta().y() or event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        bar = self.verticalScrollBar()
        step = max(bar.singleStep() * 6, 80)
        target = bar.value() - int(delta / 120 * step)
        target = max(bar.minimum(), min(bar.maximum(), target))
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(bar.value())
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()
        event.accept()


class ExplorerPanel(QWidget):
    """유형 필터와 검색을 지원하는 노트 목록 패널."""

    note_selected = Signal(str)
    note_deleted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = NoteRepository()
        self._search = SearchService()
        self._attachments = AttachmentRepository()
        self._query = ""
        self._active_type: str | None = None
        self._suppress_reorder = False

        layout = QVBoxLayout(self)

        # 유형별 필터 버튼(파스텔 알약 형태).
        filter_bar = QHBoxLayout()
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        for label in _FILTERS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._pill_style(label))
            if label == "전체":
                btn.setChecked(True)
            btn.clicked.connect(lambda _checked, lbl=label: self._on_filter(lbl))
            self._button_group.addButton(btn)
            filter_bar.addWidget(btn)
        filter_bar.addStretch(1)
        layout.addLayout(filter_bar)

        self._list = SmoothScrollListWidget(self)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setSpacing(8)
        # 드래그 앤 드롭으로 순서 변경 활성화(내부 이동).
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list, 1)

        self.refresh()

    # ----- 외부 API -------------------------------------------------------
    def _pill_style(self, label: str) -> str:
        """필터 버튼을 유형 색상의 둥근 파스텔 알약으로 스타일링한다."""
        color = NOTE_TYPE_COLORS.get(label, "#aab1bd")
        return (
            "QPushButton {"
            f" background-color: {color}; color: #ffffff; border: none;"
            " border-radius: 12px; padding: 5px 14px; font-weight: bold; }"
            "QPushButton:checked { border: 2px solid rgba(0,0,0,0.25); }"
        )

    def set_query(self, query: str) -> None:
        self._query = query or ""
        self.refresh()

    def refresh(self) -> None:
        # refresh 중에는 rowsMoved 시그널을 무시한다.
        self._suppress_reorder = True
        self._list.clear()
        notes = self._collect_notes()
        for note in notes:
            thumbnail, has_pdf = self._card_media(note.id)
            card = NoteCard(note, thumbnail=thumbnail, has_pdf=has_pdf)
            card.delete_requested.connect(self._on_delete_requested)
            item = QListWidgetItem(self._list)
            item.setSizeHint(QSize(0, max(card.sizeHint().height(), 78)))
            item.setData(256, note.id)  # Qt.UserRole
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
        self._suppress_reorder = False

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

    def _card_media(self, note_id: str) -> tuple[bytes | None, bool]:
        """카드 썸네일 바이트와 PDF 보유 여부를 반환한다."""
        try:
            image = self._attachments.first_image_for_note(note_id)
            if image is not None and image.thumbnail:
                return image.thumbnail, False
            # 이미지가 없으면 PDF 첨부 여부 확인.
            for att in self._attachments.list_for_note(note_id):
                if att.file_type == "pdf":
                    return None, True
        except Exception:
            logger.debug("첨부 미디어 조회 실패", exc_info=True)
        return None, False

    def _on_filter(self, label: str) -> None:
        self._active_type = None if label == "전체" else label
        self.refresh()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(256)
        if note_id:
            self.note_selected.emit(note_id)

    # ----- 삭제 -----------------------------------------------------------
    def _on_delete_requested(self, note_id: str) -> None:
        """삭제 버튼 클릭: 확인 다이얼로그 후 소프트 삭제한다.

        대상 사용자의 실수 방지를 위해 확인 다이얼로그를 반드시 표시한다.
        """
        note = self._repo.get_by_id(note_id)
        title = (note.title if note else "") or "제목 없음"
        answer = QMessageBox.question(
            self, "노트 삭제",
            f"'{title}' 노트를 삭제할까요?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            self._repo.delete(note_id)
        except Exception:
            logger.exception("노트 삭제 실패")
            QMessageBox.warning(self, "오류", "노트를 삭제하지 못했습니다.")
            return
        self.refresh()
        self.note_deleted.emit(note_id)

    # ----- 드래그 순서 변경 ----------------------------------------------
    def _on_rows_moved(self, *args) -> None:
        """드롭 완료 시 현재 목록 순서를 sort_order 로 영속화한다."""
        if self._suppress_reorder:
            return
        # 검색/필터가 적용된 부분 목록에서는 순서를 저장하지 않는다.
        if self._query.strip() or self._active_type:
            return
        ordered_ids = [self._list.item(row).data(256)
                       for row in range(self._list.count())]
        ordered_ids = [nid for nid in ordered_ids if nid]
        try:
            self._repo.reorder(ordered_ids)
        except Exception:
            logger.exception("노트 순서 저장 실패")
        # 위젯이 이동 중 분리될 수 있으므로 다시 그린다.
        self.refresh()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    widget = ExplorerPanel()
    widget.resize(400, 700)
    widget.show()
    sys.exit(app.exec())
