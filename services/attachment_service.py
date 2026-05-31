"""노트 첨부(이미지/PDF) 가져오기·썸네일·열기 서비스.

첨부 파일은 ``~/.zettelkasten/attachments/<note_id>/`` 에 복사 저장한다.
썸네일 생성은 CPU/IO 부하가 있으므로 UI 레이어에서 ``QThread`` 로 호출한다.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config.settings import APP_DIR
from core.attachment import Attachment
from db.repositories.attachment_repo import AttachmentRepository

logger = logging.getLogger(__name__)

ATTACH_DIR = APP_DIR / "attachments"
THUMBNAIL_WIDTH = 200  # px

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
PDF_EXTS = {".pdf"}


def detect_file_type(path: str | Path) -> str:
    """확장자로 첨부 유형을 판별한다('image' | 'pdf' | 'other')."""
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in PDF_EXTS:
        return "pdf"
    return "other"


class AttachmentService:
    """첨부 파일 복사, 썸네일 생성, 열기를 담당한다."""

    def __init__(self, base_dir: Path | str = ATTACH_DIR) -> None:
        self._repo = AttachmentRepository()
        self._base_dir = Path(base_dir)

    # ----- 첨부 추가 ------------------------------------------------------
    def add_attachment(self, note_id: str, src_path: str | Path) -> Attachment:
        """파일을 노트 폴더로 복사하고 첨부 레코드를 생성한다(썸네일 제외).

        썸네일은 :meth:`generate_thumbnail` 으로 백그라운드에서 생성한다.
        """
        src = Path(src_path)
        if not src.is_file():
            raise FileNotFoundError(f"첨부 파일을 찾을 수 없습니다: {src_path}")

        note_dir = self._base_dir / note_id
        note_dir.mkdir(parents=True, exist_ok=True)
        dest = self._unique_destination(note_dir, src.name)
        shutil.copy2(src, dest)

        file_type = detect_file_type(dest)
        return self._repo.create(note_id, str(dest), file_type)

    def _unique_destination(self, note_dir: Path, name: str) -> Path:
        """같은 이름이 있으면 ``name (1).ext`` 식으로 충돌을 피한다."""
        dest = note_dir / name
        if not dest.exists():
            return dest
        stem, suffix = Path(name).stem, Path(name).suffix
        index = 1
        while True:
            candidate = note_dir / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    # ----- 썸네일 ---------------------------------------------------------
    def generate_thumbnail(self, attachment_id: str) -> bytes | None:
        """첨부의 200px 너비 썸네일(PNG)을 생성해 저장하고 반환한다.

        QThread 에서 호출할 것. 생성에 실패하면 ``None`` 을 반환한다.
        """
        attachment = self._repo.get_by_id(attachment_id)
        if attachment is None:
            return None
        try:
            if attachment.file_type == "image":
                thumb = self._image_thumbnail(attachment.file_path)
            elif attachment.file_type == "pdf":
                thumb = self._pdf_thumbnail(attachment.file_path)
            else:
                return None
        except Exception:
            logger.exception("썸네일 생성 실패: %s", attachment.file_path)
            return None
        if thumb:
            self._repo.update_thumbnail(attachment_id, thumb)
        return thumb

    @staticmethod
    def _image_thumbnail(path: str) -> bytes | None:
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QImage
        image = QImage(path)
        if image.isNull():
            return None
        if image.width() > THUMBNAIL_WIDTH:
            image = image.scaledToWidth(THUMBNAIL_WIDTH)
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()
        return bytes(data)

    @staticmethod
    def _pdf_thumbnail(path: str) -> bytes | None:
        import fitz  # pymupdf
        doc = fitz.open(path)
        try:
            if doc.page_count == 0:
                return None
            page = doc.load_page(0)
            page_width = page.rect.width or THUMBNAIL_WIDTH
            scale = THUMBNAIL_WIDTH / page_width
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            return pixmap.tobytes("png")
        finally:
            doc.close()

    # ----- 조회/열기 ------------------------------------------------------
    def list_for_note(self, note_id: str) -> list[Attachment]:
        return self._repo.list_for_note(note_id)

    def delete_attachment(self, attachment_id: str) -> None:
        """첨부 레코드와 저장된 파일을 삭제한다."""
        attachment = self._repo.get_by_id(attachment_id)
        if attachment is None:
            return
        file_path = Path(attachment.file_path)
        self._repo.delete(attachment_id)
        try:
            if file_path.is_file():
                file_path.unlink()
        except OSError:
            logger.exception("첨부 파일 삭제 실패: %s", file_path)

    def open_attachment(self, attachment_id: str) -> None:
        """시스템 기본 뷰어로 첨부 파일을 연다."""
        attachment = self._repo.get_by_id(attachment_id)
        if attachment is None:
            raise ValueError(f"첨부를 찾을 수 없습니다: {attachment_id}")
        file_path = attachment.file_path
        if not Path(file_path).is_file():
            raise FileNotFoundError(f"첨부 파일이 사라졌습니다: {file_path}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)
        except Exception:
            logger.exception("첨부 열기 실패: %s", file_path)
            raise
