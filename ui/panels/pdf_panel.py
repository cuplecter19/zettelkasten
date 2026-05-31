"""PDF panel: thumbnail grid with import, open, link and delete actions."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QListView, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from db.repositories.pdf_repo import PdfRepository
from services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class PDFPanel(QWidget):
    """썸네일 그리드로 PDF 자산을 보여주는 패널."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = PdfRepository()
        self._service = PDFService()
        self._current_note_id: str | None = None

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        import_btn = QPushButton("PDF 가져오기")
        import_btn.clicked.connect(self._import_pdf)
        toolbar.addWidget(import_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._list = QListWidget(self)
        self._list.setViewMode(QListView.IconMode)
        self._list.setIconSize(QSize(160, 200))
        self._list.setResizeMode(QListView.Adjust)
        self._list.setSpacing(12)
        self._list.setMovement(QListView.Static)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self._list, 1)

        self.refresh()

    def set_current_note(self, note_id: str | None) -> None:
        self._current_note_id = note_id

    def refresh(self) -> None:
        self._list.clear()
        for asset in self._repo.list_all():
            item = QListWidgetItem(asset.title)
            item.setData(256, asset.id)  # Qt.UserRole
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            if asset.thumbnail:
                pixmap = QPixmap()
                pixmap.loadFromData(asset.thumbnail)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            self._list.addItem(item)

    # ----- 동작 -----------------------------------------------------------
    def _import_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF 선택", "", "PDF Files (*.pdf)")
        if not file_path:
            return
        try:
            from pathlib import Path
            title = Path(file_path).stem
            # NOTE: 큰 PDF의 경우 호출부에서 QThread 사용 권장.
            self._service.import_pdf(file_path, title,
                                     note_id=self._current_note_id)
            self.refresh()
        except Exception:
            logger.exception("PDF import failed")
            QMessageBox.warning(self, "오류", "PDF를 가져오지 못했습니다.")

    def _open_item(self, item: QListWidgetItem) -> None:
        asset_id = item.data(256)
        try:
            self._service.open_pdf(asset_id)
        except Exception:
            logger.exception("Open PDF failed")
            QMessageBox.warning(self, "오류", "PDF를 열 수 없습니다.")

    def _show_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        asset_id = item.data(256)
        menu = QMenu(self)
        link_action = menu.addAction("노트에 연결")
        delete_action = menu.addAction("삭제")
        action = menu.exec(self._list.mapToGlobal(pos))
        if action == link_action:
            self._link_to_note(asset_id)
        elif action == delete_action:
            self._delete_asset(asset_id)

    def _link_to_note(self, asset_id: str) -> None:
        if self._current_note_id is None:
            QMessageBox.information(self, "안내", "먼저 노트를 선택하세요.")
            return
        try:
            self._repo.link_to_note(asset_id, self._current_note_id)
            QMessageBox.information(self, "완료", "PDF를 현재 노트에 연결했습니다.")
        except Exception:
            logger.exception("Link PDF to note failed")
            QMessageBox.warning(self, "오류", "연결에 실패했습니다.")

    def _delete_asset(self, asset_id: str) -> None:
        try:
            self._repo.delete(asset_id)
            self.refresh()
        except Exception:
            logger.exception("Delete PDF failed")
            QMessageBox.warning(self, "오류", "삭제에 실패했습니다.")
