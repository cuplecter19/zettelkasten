"""Editor panel: title, body, auto-save, attachments and markdown preview."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, Qt, QThread, Signal
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTextBrowser,
                               QTextEdit, QToolButton, QVBoxLayout, QWidget)

from config.categories import NOTE_TYPE_COLORS
from core.note import Note
from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository
from services.attachment_service import AttachmentService
from services.classifier import NoteClassifier
from services.css_snippet_service import get_css_snippet_service
from services.markdown_service import render_document
from services.markdown_style_service import get_markdown_style_service
from ui.widgets.tag_chip import TagChip

logger = logging.getLogger(__name__)

_IMAGE_PDF_FILTER = (
    "첨부 파일 (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.pdf);;모든 파일 (*)")


class _ThumbnailWorker(QThread):
    """첨부 썸네일을 백그라운드에서 생성하는 워커."""

    done = Signal(str)  # attachment_id

    def __init__(self, service: AttachmentService, attachment_id: str,
                 parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._attachment_id = attachment_id

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            self._service.generate_thumbnail(self._attachment_id)
        except Exception:
            logger.exception("썸네일 워커 실패")
        self.done.emit(self._attachment_id)


class EditorPanel(QWidget):
    """포커스 이탈 시 자동 저장되는 노트 편집 패널."""

    note_saved = Signal(str)
    attachment_added = Signal(str)  # note_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = NoteRepository()
        self._tag_repo = TagRepository()
        self._classifier = NoteClassifier()
        self._attachments = AttachmentService()
        self._md_style = get_markdown_style_service()
        self._css_snippets = get_css_snippet_service()
        self._current_id: str | None = None
        self._suggested_type: str | None = None
        self._workers: list[_ThumbnailWorker] = []

        layout = QVBoxLayout(self)

        # 상단 툴바: 파일 첨부 / 마크다운 보기 토글.
        toolbar = QHBoxLayout()
        self._attach_btn = QPushButton("파일 첨부", self)
        self._attach_btn.clicked.connect(self._attach_file)
        toolbar.addWidget(self._attach_btn)
        self._md_toggle = QPushButton("마크다운 보기", self)
        self._md_toggle.setCheckable(True)
        self._md_toggle.toggled.connect(self._on_markdown_toggled)
        toolbar.addWidget(self._md_toggle)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

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

        # 마크다운 렌더링 미리보기(토글 시 표시).
        self._preview = QTextBrowser(self)
        self._preview.setOpenExternalLinks(True)
        self._preview.setVisible(False)
        layout.addWidget(self._preview, 1)

        # Phase 4/5 서식·스니펫이 바뀌면 미리보기가 켜져 있을 때 즉시 갱신.
        self._md_style.style_changed.connect(self._refresh_preview)
        self._css_snippets.snippets_changed.connect(self._refresh_preview)

        # PDF 등 첨부 카드 영역.
        self._attach_container = QWidget(self)
        self._attach_layout = QVBoxLayout(self._attach_container)
        self._attach_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._attach_container)

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
        # 노트를 바꾸면 마크다운 보기는 끈다(편집 우선).
        if self._md_toggle.isChecked():
            self._md_toggle.setChecked(False)
        if note is None:
            self._title.clear()
            self._body.clear()
            self._banner.setVisible(False)
            self._clear_attachment_cards()
            return
        self._title.setText(note.title)
        self._body.setPlainText(note.body)
        self._refresh_tags()
        self._refresh_attachments()
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

    # ----- 첨부 ----------------------------------------------------------
    def _attach_file(self) -> None:
        if self._current_id is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "첨부할 파일 선택", "", _IMAGE_PDF_FILTER)
        if not file_path:
            return
        try:
            attachment = self._attachments.add_attachment(
                self._current_id, file_path)
        except Exception:
            logger.exception("첨부 추가 실패")
            QMessageBox.warning(self, "오류", "파일을 첨부하지 못했습니다.")
            return

        # 이미지는 본문에 마크다운 이미지 링크를 삽입한다.
        if attachment.file_type == "image":
            self._insert_image_markdown(attachment.file_path)
            self._save()
        # 썸네일을 백그라운드에서 생성.
        self._start_thumbnail_worker(attachment.id)
        self._refresh_attachments()
        self.attachment_added.emit(self._current_id)

    def _insert_image_markdown(self, path: str) -> None:
        cursor = self._body.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        prefix = "\n" if self._body.toPlainText().strip() else ""
        cursor.insertText(f"{prefix}![]({path})\n")
        self._body.setTextCursor(cursor)

    def _start_thumbnail_worker(self, attachment_id: str) -> None:
        worker = _ThumbnailWorker(self._attachments, attachment_id, self)
        worker.done.connect(self._on_thumbnail_done)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        self._workers.append(worker)
        worker.start()

    def _on_thumbnail_done(self, _attachment_id: str) -> None:
        # 썸네일이 준비되면 첨부 카드/카드 미디어를 갱신한다.
        self._refresh_attachments()
        if self._current_id is not None:
            self.attachment_added.emit(self._current_id)

    def _cleanup_worker(self, worker: _ThumbnailWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def _clear_attachment_cards(self) -> None:
        while self._attach_layout.count():
            item = self._attach_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_attachments(self) -> None:
        """PDF/기타 첨부를 카드로 표시한다(이미지는 본문에 인라인)."""
        self._clear_attachment_cards()
        if self._current_id is None:
            return
        for att in self._attachments.list_for_note(self._current_id):
            if att.file_type == "image":
                continue
            self._attach_layout.addWidget(self._build_attachment_card(att))

    def _build_attachment_card(self, attachment) -> QFrame:
        from pathlib import Path
        card = QFrame(self)
        card.setObjectName("AttachmentCard")
        card.setStyleSheet(
            "#AttachmentCard { border: 1px solid #444; border-radius: 4px; }")
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 4, 8, 4)
        label = QLabel(Path(attachment.file_path).name, card)
        row.addWidget(label, 1)
        open_btn = QToolButton(card)
        open_btn.setText("열기")
        open_btn.clicked.connect(
            lambda _checked=False, aid=attachment.id: self._open_attachment(aid))
        row.addWidget(open_btn)
        return card

    def _open_attachment(self, attachment_id: str) -> None:
        try:
            self._attachments.open_attachment(attachment_id)
        except Exception:
            logger.exception("첨부 열기 실패")
            QMessageBox.warning(self, "오류", "첨부 파일을 열 수 없습니다.")

    # ----- 마크다운 보기 -------------------------------------------------
    def _markdown_css(self) -> str:
        """Phase 4 서식 CSS 와 Phase 5 활성 스니펫 CSS 를 합친다."""
        return f"{self._md_style.build_css()}\n{self._css_snippets.build_css()}"

    def _render_preview(self) -> None:
        self._preview.setHtml(
            render_document(self._body.toPlainText(), self._markdown_css()))

    def _refresh_preview(self) -> None:
        """미리보기가 표시 중일 때만 다시 렌더링한다."""
        if self._preview.isVisible():
            self._render_preview()

    def _on_markdown_toggled(self, checked: bool) -> None:
        if checked:
            self._render_preview()
            self._body.setVisible(False)
            self._preview.setVisible(True)
        else:
            self._body.setVisible(True)
            self._preview.setVisible(False)

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


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    widget = EditorPanel()
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec())
