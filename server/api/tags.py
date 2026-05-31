"""태그 및 노트-태그 연결 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Connection

from auth import get_current_device
from database_server import db_dependency

router = APIRouter(tags=["tags"])


class TagIn(BaseModel):
    name: str
    color: str | None = None


class TagOut(BaseModel):
    id: int
    name: str
    color: str | None = None


@router.get("/tags", response_model=list[TagOut])
def list_tags(conn: Connection = Depends(db_dependency),
              device: str = Depends(get_current_device)) -> list[TagOut]:
    rows = conn.execute(text("SELECT id, name, color FROM tags ORDER BY name")).all()
    return [TagOut(id=r.id, name=r.name, color=r.color) for r in rows]


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagIn, conn: Connection = Depends(db_dependency),
               device: str = Depends(get_current_device)) -> TagOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "태그 이름이 필요합니다.")
    existing = conn.execute(text("SELECT id, name, color FROM tags WHERE name=:n"),
                            {"n": name}).first()
    if existing is not None:
        return TagOut(id=existing.id, name=existing.name, color=existing.color)
    result = conn.execute(text("INSERT INTO tags (name, color) VALUES (:n, :c)"),
                          {"n": name, "c": payload.color})
    tag_id = result.lastrowid
    return TagOut(id=tag_id, name=name, color=payload.color)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, conn: Connection = Depends(db_dependency),
               device: str = Depends(get_current_device)) -> None:
    conn.execute(text("DELETE FROM tags WHERE id=:id"), {"id": tag_id})


@router.post("/notes/{note_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
def link_tag(note_id: str, payload: TagIn,
             conn: Connection = Depends(db_dependency),
             device: str = Depends(get_current_device)) -> None:
    name = payload.name.strip()
    tag = conn.execute(text("SELECT id FROM tags WHERE name=:n"), {"n": name}).first()
    if tag is None:
        result = conn.execute(text("INSERT INTO tags (name, color) VALUES (:n, :c)"),
                              {"n": name, "c": payload.color})
        tag_id = result.lastrowid
    else:
        tag_id = tag.id
    conn.execute(text(
        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (:nid, :tid)"
    ), {"nid": note_id, "tid": tag_id})


@router.delete("/notes/{note_id}/tags/{tag_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def unlink_tag(note_id: str, tag_id: int,
               conn: Connection = Depends(db_dependency),
               device: str = Depends(get_current_device)) -> None:
    conn.execute(text(
        "DELETE FROM note_tags WHERE note_id=:nid AND tag_id=:tid"
    ), {"nid": note_id, "tid": tag_id})
