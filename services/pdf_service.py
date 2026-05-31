"""PDF import / thumbnail / open service using pymupdf (fitz).

Thumbnail rendering and text extraction are CPU bound and should be invoked
from a ``QThread`` by the UI layer to avoid blocking.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import fitz  # pymupdf

from core.pdf_asset import PdfAsset
from db.repositories.pdf_repo import PdfRepository

logger = logging.getLogger(__name__)

THUMBNAIL_WIDTH = 200  # px


class PDFService:
    """PDF 자산을 가져오고 썸네일/텍스트를 관리한다."""

    def __init__(self) -> None:
        self._repo = PdfRepository()

    def import_pdf(self, file_path: str, title: str,
                   note_id: str | None = None) -> PdfAsset:
        """첫 페이지 썸네일(PNG, 200px 너비)과 텍스트를 추출해 DB에 저장한다.

        QThread에서 호출할 것.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        try:
            doc = fitz.open(str(path))
        except Exception as exc:  # pymupdf 는 다양한 예외를 던진다.
            logger.exception("Failed to open PDF: %s", file_path)
            raise ValueError(f"Invalid PDF file: {file_path}") from exc

        try:
            if doc.page_count == 0:
                raise ValueError(f"PDF has no pages: {file_path}")

            first_page = doc.load_page(0)

            # 200px 너비에 맞춘 스케일로 렌더링.
            page_width = first_page.rect.width or THUMBNAIL_WIDTH
            scale = THUMBNAIL_WIDTH / page_width
            matrix = fitz.Matrix(scale, scale)
            pixmap = first_page.get_pixmap(matrix=matrix)
            thumbnail = pixmap.tobytes("png")

            text_parts = [page.get_text() for page in doc]
            extracted_text = "\n".join(text_parts).strip()
        finally:
            doc.close()

        return self._repo.create(
            file_path=str(path),
            title=title,
            thumbnail=thumbnail,
            extracted_text=extracted_text,
            note_id=note_id,
        )

    def get_thumbnail(self, asset_id: str) -> bytes:
        asset = self._repo.get_by_id(asset_id)
        if asset is None:
            raise ValueError(f"PdfAsset not found: {asset_id}")
        return asset.thumbnail or b""

    def open_pdf(self, asset_id: str) -> None:
        """시스템 기본 PDF 뷰어로 연다."""
        asset = self._repo.get_by_id(asset_id)
        if asset is None:
            raise ValueError(f"PdfAsset not found: {asset_id}")

        file_path = asset.file_path
        if not Path(file_path).is_file():
            raise FileNotFoundError(f"PDF file missing on disk: {file_path}")

        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)
        except Exception:
            logger.exception("Failed to open PDF: %s", file_path)
            raise
