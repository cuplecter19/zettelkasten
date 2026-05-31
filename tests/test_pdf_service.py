"""Tests for the PDF import service."""

from __future__ import annotations

import fitz
import pytest

from services.pdf_service import PDFService


def _make_sample_pdf(path) -> str:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello Zettelkasten PDF 테스트")
    doc.save(str(path))
    doc.close()
    return str(path)


def test_import_pdf_creates_thumbnail(db, tmp_path):
    pdf_path = _make_sample_pdf(tmp_path / "sample.pdf")
    service = PDFService()

    asset = service.import_pdf(pdf_path, "샘플 PDF")

    assert asset.id is not None
    assert asset.thumbnail is not None
    assert len(asset.thumbnail) > 0
    assert asset.extracted_text and "Zettelkasten" in asset.extracted_text


def test_get_thumbnail_returns_bytes(db, tmp_path):
    pdf_path = _make_sample_pdf(tmp_path / "sample.pdf")
    service = PDFService()
    asset = service.import_pdf(pdf_path, "샘플 PDF")

    data = service.get_thumbnail(asset.id)
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_import_pdf_invalid_path_raises(db):
    service = PDFService()
    with pytest.raises(FileNotFoundError):
        service.import_pdf("/nonexistent/path/to/file.pdf", "없는 파일")
