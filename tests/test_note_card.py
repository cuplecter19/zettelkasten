"""Phase 2-2 / 3-2: 노트 카드 삭제 버튼 및 썸네일 표시 테스트."""

from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox

from core.note import Note
from db.repositories.note_repo import NoteRepository
from ui.panels.explorer_panel import ExplorerPanel
from ui.widgets.note_card import NoteCard


def _png_bytes() -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    image = QImage(40, 40, QImage.Format_RGB32)
    image.fill(0x00FF00)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def test_card_emits_delete_requested(qtbot):
    note = Note(id="n1", title="제목", body="본문", note_type="IDEA")
    card = NoteCard(note)
    qtbot.addWidget(card)
    received = []
    card.delete_requested.connect(received.append)
    card._delete_btn.click()
    assert received == ["n1"]


def test_card_shows_image_thumbnail(qtbot):
    from PySide6.QtWidgets import QLabel
    note = Note(id="n2", title="이미지", body="", note_type="IDEA")
    card = NoteCard(note, thumbnail=_png_bytes())
    qtbot.addWidget(card)
    # 픽스맵을 가진 QLabel(썸네일)이 존재해야 한다.
    has_pixmap = any(
        not lbl.pixmap().isNull()
        for lbl in card.findChildren(QLabel) if lbl.pixmap() is not None)
    assert has_pixmap


def test_card_shows_pdf_icon_when_only_pdf(qtbot):
    from PySide6.QtWidgets import QLabel
    note = Note(id="n3", title="피디에프", body="", note_type="ARCHIVE")
    card = NoteCard(note, thumbnail=None, has_pdf=True)
    qtbot.addWidget(card)
    has_pixmap = any(
        not lbl.pixmap().isNull()
        for lbl in card.findChildren(QLabel) if lbl.pixmap() is not None)
    assert has_pixmap


def test_explorer_delete_confirmed_soft_deletes(qtbot, db, monkeypatch):
    repo = NoteRepository()
    note = repo.create("삭제할 노트", "본문", "IDEA")
    panel = ExplorerPanel()
    qtbot.addWidget(panel)

    # 확인 다이얼로그를 Yes 로 자동 응답.
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.Yes)
    deleted = []
    panel.note_deleted.connect(deleted.append)

    panel._on_delete_requested(note.id)

    assert deleted == [note.id]
    assert repo.get_by_id(note.id).deleted_at is not None
    assert all(n.id != note.id for n in repo.list_all())


def test_explorer_delete_cancelled_keeps_note(qtbot, db, monkeypatch):
    repo = NoteRepository()
    note = repo.create("유지할 노트", "본문", "IDEA")
    panel = ExplorerPanel()
    qtbot.addWidget(panel)

    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.No)
    panel._on_delete_requested(note.id)

    assert repo.get_by_id(note.id).deleted_at is None
