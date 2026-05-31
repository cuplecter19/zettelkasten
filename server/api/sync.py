"""핵심 동기화 엔드포인트(push / pull).

충돌 처리는 ``updated_at`` 기준 최신 우선(Last Write Wins)이다. push 시 서버의
``updated_at`` 이 더 최신이면 서버 버전을 유지하고 해당 레코드를 충돌 목록으로
반환한다. 로컬 앱은 이를 받아 자신의 DB 를 서버 버전으로 덮어쓴다.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection

from auth import get_current_device
from database_server import db_dependency

router = APIRouter(tags=["sync"])


def parse_dt(value: Any) -> datetime | None:
    """문자열/datetime 을 naive ``datetime`` 으로 변환한다."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text_value = str(value).replace("Z", "")
    try:
        return datetime.fromisoformat(text_value)
    except ValueError:
        # 보조 포맷.
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text_value, fmt)
            except ValueError:
                continue
    return None


class Changes(BaseModel):
    notes: list[dict] = Field(default_factory=list)
    tags: list[dict] = Field(default_factory=list)
    note_tags: list[dict] = Field(default_factory=list)
    note_links: list[dict] = Field(default_factory=list)
    pdf_assets: list[dict] = Field(default_factory=list)


class PushRequest(BaseModel):
    device_id: str
    last_sync_at: datetime | None = None
    changes: Changes = Field(default_factory=Changes)


class PushResponse(BaseModel):
    applied: int
    conflicts: list[dict]


class PullRequest(BaseModel):
    device_id: str
    last_sync_at: datetime | None = None


class PullResponse(BaseModel):
    server_time: datetime
    notes: list[dict]
    tags: list[dict]
    note_tags: list[dict]
    note_links: list[dict]
    pdf_assets: list[dict]


# ----- push ----------------------------------------------------------------
def _apply_note(conn: Connection, note: dict, device: str) -> dict | None:
    """단일 노트를 LWW 로 반영한다. 충돌(서버 우선) 시 서버 레코드를 반환."""
    incoming_updated = parse_dt(note.get("updated_at")) or datetime.min
    row = conn.execute(text("SELECT * FROM notes WHERE id=:id"),
                       {"id": note["id"]}).first()
    if row is not None:
        server_updated = parse_dt(row.updated_at) or datetime.min
        if server_updated > incoming_updated:
            # 서버 버전이 더 최신 → 서버 유지, 충돌로 반환.
            return _note_row_to_dict(row)

    deleted = note.get("deleted") or note.get("deleted_at")
    deleted_at = (parse_dt(note.get("deleted_at"))
                  or (incoming_updated if note.get("deleted") else None))
    params = {
        "id": note["id"],
        "title": note.get("title", "제목 없음"),
        "body": note.get("body", ""),
        "note_type": note.get("note_type", "IDEA"),
        "is_pinned": int(bool(note.get("is_pinned", False))),
        "color_hint": note.get("color_hint"),
        "created_at": parse_dt(note.get("created_at")) or incoming_updated,
        "updated_at": incoming_updated,
        "deleted_at": deleted_at if deleted else None,
        "device": device,
    }
    conn.execute(text(
        "INSERT INTO notes (id, title, body, note_type, is_pinned, color_hint, "
        "created_at, updated_at, deleted_at, last_synced_by) "
        "VALUES (:id, :title, :body, :note_type, :is_pinned, :color_hint, "
        ":created_at, :updated_at, :deleted_at, :device) "
        "ON CONFLICT(id) DO UPDATE SET title=excluded.title, body=excluded.body, "
        "note_type=excluded.note_type, is_pinned=excluded.is_pinned, "
        "color_hint=excluded.color_hint, updated_at=excluded.updated_at, "
        "deleted_at=excluded.deleted_at, last_synced_by=excluded.last_synced_by"
    ), params)
    return None


def _apply_pdf(conn: Connection, pdf: dict, device: str) -> dict | None:
    incoming_updated = parse_dt(pdf.get("updated_at")) or \
        parse_dt(pdf.get("created_at")) or datetime.min
    row = conn.execute(text("SELECT * FROM pdf_assets WHERE id=:id"),
                       {"id": pdf["id"]}).first()
    if row is not None:
        server_updated = parse_dt(row.created_at) or datetime.min
        if server_updated > incoming_updated and not pdf.get("deleted"):
            return _pdf_row_to_dict(row)

    deleted = pdf.get("deleted") or pdf.get("deleted_at")
    conn.execute(text(
        "INSERT INTO pdf_assets (id, file_path, title, extracted_text, note_id, "
        "created_at, deleted_at, last_synced_by) "
        "VALUES (:id, :fp, :title, :txt, :nid, :created_at, :deleted_at, :device) "
        "ON CONFLICT(id) DO UPDATE SET title=excluded.title, "
        "extracted_text=excluded.extracted_text, note_id=excluded.note_id, "
        "deleted_at=excluded.deleted_at, last_synced_by=excluded.last_synced_by"
    ), {
        "id": pdf["id"],
        "fp": pdf.get("file_path", ""),
        "title": pdf.get("title", ""),
        "txt": pdf.get("extracted_text"),
        "nid": pdf.get("note_id"),
        "created_at": parse_dt(pdf.get("created_at")) or incoming_updated,
        "deleted_at": parse_dt(pdf.get("deleted_at")) or
        (incoming_updated if pdf.get("deleted") else None),
        "device": device,
    })
    return None


@router.post("/sync/push", response_model=PushResponse)
def push(req: PushRequest, conn: Connection = Depends(db_dependency),
         device: str = Depends(get_current_device)) -> PushResponse:
    conflicts: list[dict] = []
    applied = 0

    for note in req.changes.notes:
        if "id" not in note:
            continue
        conflict = _apply_note(conn, note, device)
        if conflict is not None:
            conflicts.append({"table": "notes", "record": conflict})
        else:
            applied += 1

    for tag in req.changes.tags:
        name = (tag.get("name") or "").strip()
        if not name:
            continue
        conn.execute(text(
            "INSERT OR IGNORE INTO tags (name, color) VALUES (:n, :c)"
        ), {"n": name, "c": tag.get("color")})
        applied += 1

    for link in req.changes.note_tags:
        if not link.get("note_id") or link.get("tag_id") is None:
            continue
        conn.execute(text(
            "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (:nid, :tid)"
        ), {"nid": link["note_id"], "tid": link["tag_id"]})
        applied += 1

    for link in req.changes.note_links:
        if not link.get("source_id") or not link.get("target_id"):
            continue
        conn.execute(text(
            "INSERT OR IGNORE INTO note_links (source_id, target_id, link_type) "
            "VALUES (:s, :t, :lt)"
        ), {"s": link["source_id"], "t": link["target_id"],
            "lt": link.get("link_type", "related")})
        applied += 1

    for pdf in req.changes.pdf_assets:
        if "id" not in pdf:
            continue
        conflict = _apply_pdf(conn, pdf, device)
        if conflict is not None:
            conflicts.append({"table": "pdf_assets", "record": conflict})
        else:
            applied += 1

    return PushResponse(applied=applied, conflicts=conflicts)


# ----- pull ----------------------------------------------------------------
def _note_row_to_dict(row) -> dict:
    return {
        "id": row.id, "title": row.title, "body": row.body,
        "note_type": row.note_type, "is_pinned": bool(row.is_pinned),
        "color_hint": row.color_hint,
        "created_at": str(row.created_at) if row.created_at else None,
        "updated_at": str(row.updated_at) if row.updated_at else None,
        "deleted_at": str(row.deleted_at) if row.deleted_at else None,
        "deleted": row.deleted_at is not None,
    }


def _pdf_row_to_dict(row) -> dict:
    return {
        "id": row.id, "file_path": row.file_path, "title": row.title,
        "extracted_text": row.extracted_text, "note_id": row.note_id,
        "created_at": str(row.created_at) if row.created_at else None,
        "deleted_at": str(row.deleted_at) if row.deleted_at else None,
        "deleted": row.deleted_at is not None,
    }


@router.post("/sync/pull", response_model=PullResponse)
def pull(req: PullRequest, conn: Connection = Depends(db_dependency),
         device: str = Depends(get_current_device)) -> PullResponse:
    since = req.last_sync_at
    note_q = "SELECT * FROM notes"
    pdf_q = "SELECT * FROM pdf_assets"
    params: dict = {}
    if since is not None:
        note_q += " WHERE updated_at > :since OR deleted_at > :since"
        pdf_q += " WHERE created_at > :since OR deleted_at > :since"
        params["since"] = since

    notes = [_note_row_to_dict(r) for r in conn.execute(text(note_q), params).all()]
    pdfs = [_pdf_row_to_dict(r) for r in conn.execute(text(pdf_q), params).all()]

    tags = [{"id": r.id, "name": r.name, "color": r.color}
            for r in conn.execute(text("SELECT id, name, color FROM tags")).all()]
    note_tags = [{"note_id": r.note_id, "tag_id": r.tag_id}
                 for r in conn.execute(
                     text("SELECT note_id, tag_id FROM note_tags")).all()]
    note_links = [{"source_id": r.source_id, "target_id": r.target_id,
                   "link_type": r.link_type}
                  for r in conn.execute(text(
                      "SELECT source_id, target_id, link_type FROM note_links")).all()]

    return PullResponse(
        server_time=datetime.now(),
        notes=notes, tags=tags, note_tags=note_tags,
        note_links=note_links, pdf_assets=pdfs,
    )
