"""PDF 자산 업로드/다운로드/삭제 엔드포인트.

서버는 pymupdf 처리를 하지 않는다. 로컬 앱이 생성한 썸네일·추출 텍스트를
메타데이터와 함께 받는다. 파일 본문은 ``asset_id`` 기반 경로로 저장하여
경로 조작(path traversal)을 방지한다.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Connection

from auth import get_current_device
from config_server import PDF_DIR
from database_server import db_dependency

router = APIRouter(tags=["pdfs"])


class PdfMeta(BaseModel):
    id: str
    title: str
    note_id: str | None = None
    created_at: datetime | None = None


def _stored_path(asset_id: str) -> Path:
    # asset_id 는 서버에서 생성하거나 UUID 형식으로 검증하여 경로 조작을 막는다.
    return PDF_DIR / f"{asset_id}.pdf"


def _safe_asset_id(asset_id: str | None) -> str:
    if asset_id:
        try:
            return str(uuid.UUID(asset_id))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "잘못된 asset_id 형식입니다.") from exc
    return str(uuid.uuid4())


@router.post("/pdfs/upload", status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    asset_id: str | None = Form(None),
    note_id: str | None = Form(None),
    extracted_text: str | None = Form(None),
    conn: Connection = Depends(db_dependency),
    device: str = Depends(get_current_device),
) -> PdfMeta:
    asset_id = _safe_asset_id(asset_id)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    dest = _stored_path(asset_id)
    content = await file.read()
    dest.write_bytes(content)

    now = datetime.now()
    conn.execute(text(
        "INSERT INTO pdf_assets (id, file_path, title, extracted_text, note_id, "
        "created_at, last_synced_by) "
        "VALUES (:id, :fp, :title, :txt, :nid, :now, :device) "
        "ON CONFLICT(id) DO UPDATE SET file_path=excluded.file_path, "
        "title=excluded.title, extracted_text=excluded.extracted_text, "
        "note_id=excluded.note_id, last_synced_by=excluded.last_synced_by, "
        "deleted_at=NULL"
    ), {
        "id": asset_id, "fp": str(dest), "title": title,
        "txt": extracted_text, "nid": note_id, "now": now, "device": device,
    })
    return PdfMeta(id=asset_id, title=title, note_id=note_id, created_at=now)


@router.get("/pdfs", response_model=list[PdfMeta])
def list_pdfs(conn: Connection = Depends(db_dependency),
              device: str = Depends(get_current_device)) -> list[PdfMeta]:
    rows = conn.execute(text(
        "SELECT id, title, note_id, created_at FROM pdf_assets "
        "WHERE deleted_at IS NULL ORDER BY created_at DESC"
    )).all()
    return [PdfMeta(id=r.id, title=r.title, note_id=r.note_id,
                    created_at=r.created_at) for r in rows]


@router.get("/pdfs/{asset_id}/file")
def download_pdf(asset_id: str, conn: Connection = Depends(db_dependency),
                 device: str = Depends(get_current_device)) -> StreamingResponse:
    row = conn.execute(text(
        "SELECT file_path FROM pdf_assets WHERE id=:id AND deleted_at IS NULL"
    ), {"id": asset_id}).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF 를 찾을 수 없습니다.")
    path = _stored_path(asset_id)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF 파일이 없습니다.")

    def _iter():
        with path.open("rb") as fh:
            while chunk := fh.read(64 * 1024):
                yield chunk

    return StreamingResponse(_iter(), media_type="application/pdf")


@router.delete("/pdfs/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pdf(asset_id: str, conn: Connection = Depends(db_dependency),
               device: str = Depends(get_current_device)) -> None:
    conn.execute(text(
        "UPDATE pdf_assets SET deleted_at=:now, last_synced_by=:device "
        "WHERE id=:id AND deleted_at IS NULL"
    ), {"id": asset_id, "now": datetime.now(), "device": device})
