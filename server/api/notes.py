"""노트 CRUD 엔드포인트."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Connection

from auth import get_current_device
from database_server import db_dependency

router = APIRouter(tags=["notes"])

VALID_TYPES = {"LEARNING", "IDEA", "MOOD", "ARCHIVE"}


class NoteIn(BaseModel):
    id: str | None = None
    title: str = "제목 없음"
    body: str = ""
    note_type: str = "IDEA"
    is_pinned: bool = False
    color_hint: str | None = None


class NoteOut(BaseModel):
    id: str
    title: str
    body: str
    note_type: str
    is_pinned: bool
    color_hint: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _row_to_note(row) -> NoteOut:
    return NoteOut(
        id=row.id,
        title=row.title,
        body=row.body,
        note_type=row.note_type,
        is_pinned=bool(row.is_pinned),
        color_hint=row.color_hint,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/notes", response_model=list[NoteOut])
def list_notes(conn: Connection = Depends(db_dependency),
               device: str = Depends(get_current_device)) -> list[NoteOut]:
    rows = conn.execute(text(
        "SELECT * FROM notes WHERE deleted_at IS NULL "
        "ORDER BY is_pinned DESC, updated_at DESC"
    )).all()
    return [_row_to_note(r) for r in rows]


@router.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: str, conn: Connection = Depends(db_dependency),
             device: str = Depends(get_current_device)) -> NoteOut:
    row = conn.execute(
        text("SELECT * FROM notes WHERE id = :id AND deleted_at IS NULL"),
        {"id": note_id},
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "노트를 찾을 수 없습니다.")
    return _row_to_note(row)


@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteIn, conn: Connection = Depends(db_dependency),
                device: str = Depends(get_current_device)) -> NoteOut:
    if payload.note_type not in VALID_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "잘못된 note_type 입니다.")
    import uuid
    note_id = payload.id or str(uuid.uuid4())
    now = datetime.now()
    conn.execute(text(
        "INSERT INTO notes (id, title, body, note_type, is_pinned, color_hint, "
        "created_at, updated_at, last_synced_by) "
        "VALUES (:id, :title, :body, :note_type, :is_pinned, :color_hint, "
        ":created_at, :updated_at, :device)"
    ), {
        "id": note_id, "title": payload.title, "body": payload.body,
        "note_type": payload.note_type, "is_pinned": int(payload.is_pinned),
        "color_hint": payload.color_hint, "created_at": now, "updated_at": now,
        "device": device,
    })
    row = conn.execute(text("SELECT * FROM notes WHERE id = :id"),
                       {"id": note_id}).first()
    return _row_to_note(row)


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: str, payload: NoteIn,
                conn: Connection = Depends(db_dependency),
                device: str = Depends(get_current_device)) -> NoteOut:
    if payload.note_type not in VALID_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "잘못된 note_type 입니다.")
    exists = conn.execute(text("SELECT id FROM notes WHERE id = :id"),
                          {"id": note_id}).first()
    if exists is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "노트를 찾을 수 없습니다.")
    conn.execute(text(
        "UPDATE notes SET title=:title, body=:body, note_type=:note_type, "
        "is_pinned=:is_pinned, color_hint=:color_hint, updated_at=:updated_at, "
        "last_synced_by=:device WHERE id=:id"
    ), {
        "id": note_id, "title": payload.title, "body": payload.body,
        "note_type": payload.note_type, "is_pinned": int(payload.is_pinned),
        "color_hint": payload.color_hint, "updated_at": datetime.now(),
        "device": device,
    })
    row = conn.execute(text("SELECT * FROM notes WHERE id = :id"),
                       {"id": note_id}).first()
    return _row_to_note(row)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, conn: Connection = Depends(db_dependency),
                device: str = Depends(get_current_device)) -> None:
    now = datetime.now()
    conn.execute(text(
        "UPDATE notes SET deleted_at=:now, updated_at=:now, last_synced_by=:device "
        "WHERE id=:id AND deleted_at IS NULL"
    ), {"id": note_id, "now": now, "device": device})
