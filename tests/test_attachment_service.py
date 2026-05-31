"""Phase 3-1: 첨부 서비스 및 저장소 테스트."""

from __future__ import annotations

import fitz
from PySide6.QtGui import QImage

from db.repositories.attachment_repo import AttachmentRepository
from db.repositories.note_repo import NoteRepository
from services.attachment_service import AttachmentService, detect_file_type


def _make_image(path) -> str:
    image = QImage(300, 200, QImage.Format_RGB32)
    image.fill(0xFF3366)
    image.save(str(path), "PNG")
    return str(path)


def _make_pdf(path) -> str:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "첨부 PDF 테스트")
    doc.save(str(path))
    doc.close()
    return str(path)


def test_detect_file_type():
    assert detect_file_type("a.png") == "image"
    assert detect_file_type("b.JPG") == "image"
    assert detect_file_type("c.pdf") == "pdf"
    assert detect_file_type("d.txt") == "other"


def test_add_image_attachment_copies_and_records(qtbot, db, tmp_path):
    note = NoteRepository().create("노트", "본문", "IDEA")
    src = _make_image(tmp_path / "pic.png")
    svc = AttachmentService(tmp_path / "attach")

    att = svc.add_attachment(note.id, src)
    assert att.file_type == "image"
    # note_id 폴더 아래에 복사된다.
    assert (tmp_path / "attach" / note.id).exists()
    assert att.file_path.endswith(".png")


def test_generate_image_thumbnail(qtbot, db, tmp_path):
    note = NoteRepository().create("노트", "본문", "IDEA")
    src = _make_image(tmp_path / "pic.png")
    svc = AttachmentService(tmp_path / "attach")
    att = svc.add_attachment(note.id, src)

    thumb = svc.generate_thumbnail(att.id)
    assert thumb and len(thumb) > 0
    # DB 에도 저장된다.
    assert AttachmentRepository().get_by_id(att.id).thumbnail == thumb


def test_generate_pdf_thumbnail(qtbot, db, tmp_path):
    note = NoteRepository().create("노트", "본문", "IDEA")
    src = _make_pdf(tmp_path / "doc.pdf")
    svc = AttachmentService(tmp_path / "attach")
    att = svc.add_attachment(note.id, src)
    assert att.file_type == "pdf"

    thumb = svc.generate_thumbnail(att.id)
    assert thumb and len(thumb) > 0


def test_first_image_for_note(qtbot, db, tmp_path):
    repo = AttachmentRepository()
    note = NoteRepository().create("노트", "본문", "IDEA")
    svc = AttachmentService(tmp_path / "attach")
    img = svc.add_attachment(note.id, _make_image(tmp_path / "pic.png"))
    svc.add_attachment(note.id, _make_pdf(tmp_path / "doc.pdf"))

    first = repo.first_image_for_note(note.id)
    assert first is not None and first.id == img.id
    assert repo.has_attachments(note.id) is True


def test_add_attachment_missing_file_raises(qtbot, db, tmp_path):
    note = NoteRepository().create("노트", "본문", "IDEA")
    svc = AttachmentService(tmp_path / "attach")
    try:
        svc.add_attachment(note.id, "/no/such/file.png")
        assert False, "FileNotFoundError expected"
    except FileNotFoundError:
        pass
