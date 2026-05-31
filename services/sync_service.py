"""로컬 앱 ↔ 클라우드 서버 양방향 동기화 서비스.

설계 원칙
---------
* 오프라인 시 로컬 DB 로 독립 작동하고, 온라인 복귀 시 자동 동기화한다.
* 충돌은 ``updated_at`` 기준 최신 우선(Last Write Wins)으로 처리한다. 서버에서
  충돌이 보고되면(서버가 더 최신) 로컬을 서버 버전으로 덮어쓴다.
* HTTP 요청은 반드시 ``QThread`` 안에서 동기(sync) ``httpx`` 클라이언트로
  수행한다. 메인 스레드에서 보내면 UI 가 멈춘다.
* PDF 파일은 메타데이터(/api/sync/push)와 본문(/api/pdfs/upload)을 분리 전송한다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from sqlalchemy import text

from db.database import get_session
from db.repositories.note_repo import NoteRepository
from db.repositories.pdf_repo import PdfRepository

logger = logging.getLogger(__name__)

HEALTH_TIMEOUT = 3.0   # 초
REQUEST_TIMEOUT = 30.0  # 초


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class SyncService(QObject):
    """서버와 양방향 동기화를 수행한다."""

    # UI 상태 표시용 시그널: "online" | "offline" | "syncing"
    status_changed = Signal(str)
    sync_completed = Signal(dict)

    def __init__(self, server_url: str, device_id: str, token: str,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_url = server_url.rstrip("/")
        self._device_id = device_id
        self._token = token
        self._notes = NoteRepository()
        self._pdfs = PdfRepository()

        self._thread: QThread | None = None
        self._timer: QTimer | None = None
        self._workers: list[QThread] = []

    # ----- 기본 정보 ------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._token}

    def _url(self, path: str) -> str:
        return f"{self._server_url}{path}"

    def is_online(self) -> bool:
        """``GET /api/health`` 로 서버 접속 가능 여부를 확인한다(타임아웃 3초)."""
        try:
            resp = httpx.get(self._url("/api/health"), timeout=HEALTH_TIMEOUT)
            online = resp.status_code == 200
        except httpx.HTTPError:
            online = False
        self.status_changed.emit("online" if online else "offline")
        return online

    # ----- 로컬 변경분 수집 ----------------------------------------------
    def _collect_changes(self, since: datetime | None) -> dict:
        notes = []
        for note in self._notes.list_changed_since(since):
            notes.append({
                "id": note.id,
                "title": note.title,
                "body": note.body,
                "note_type": note.note_type,
                "is_pinned": bool(note.is_pinned),
                "color_hint": note.color_hint,
                "created_at": _iso(note.created_at),
                "updated_at": _iso(note.updated_at),
                "deleted_at": _iso(note.deleted_at),
                "deleted": note.deleted_at is not None,
            })

        with get_session() as session:
            tags = [{"id": r.id, "name": r.name, "color": r.color}
                    for r in session.execute(
                        text("SELECT id, name, color FROM tags"))]
            note_tags = [{"note_id": r.note_id, "tag_id": r.tag_id}
                         for r in session.execute(
                             text("SELECT note_id, tag_id FROM note_tags"))]
            note_links = [{"source_id": r.source_id, "target_id": r.target_id,
                           "link_type": r.link_type}
                          for r in session.execute(text(
                              "SELECT source_id, target_id, link_type "
                              "FROM note_links"))]
            pdf_rows = session.execute(text(
                "SELECT id, file_path, title, extracted_text, note_id, "
                "created_at, deleted_at FROM pdf_assets"))
            pdf_assets = [{
                "id": r.id, "file_path": r.file_path, "title": r.title,
                "extracted_text": r.extracted_text, "note_id": r.note_id,
                "created_at": _iso(r.created_at),
                "deleted_at": _iso(r.deleted_at),
                "deleted": r.deleted_at is not None,
            } for r in pdf_rows]

        return {
            "notes": notes, "tags": tags, "note_tags": note_tags,
            "note_links": note_links, "pdf_assets": pdf_assets,
        }

    # ----- push ----------------------------------------------------------
    def push_changes(self, since: datetime | None) -> dict:
        """``since`` 이후 로컬 변경분을 서버에 전송한다.

        반환된 충돌 목록을 로그에 기록하고 로컬을 서버 버전으로 덮어쓴다.
        """
        payload = {
            "device_id": self._device_id,
            "last_sync_at": _iso(since),
            "changes": self._collect_changes(since),
        }
        resp = httpx.post(self._url("/api/sync/push"), json=payload,
                          headers=self._headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        conflicts = data.get("conflicts", [])
        if conflicts:
            logger.warning("동기화 충돌 %d건: 서버 버전으로 덮어씁니다.",
                           len(conflicts))
            self._apply_conflicts(conflicts)
        return data

    def _apply_conflicts(self, conflicts: list[dict]) -> None:
        for item in conflicts:
            table = item.get("table")
            record = item.get("record", {})
            if table == "notes":
                self._notes.upsert_remote(self._normalise_note(record))
            elif table == "pdf_assets":
                self._upsert_pdf(record)

    # ----- pull ----------------------------------------------------------
    def pull_changes(self, since: datetime | None) -> int:
        """서버 변경분을 가져와 로컬 DB 에 upsert 한다. 적용 건수를 반환."""
        payload = {
            "device_id": self._device_id,
            "last_sync_at": _iso(since),
        }
        resp = httpx.post(self._url("/api/sync/pull"), json=payload,
                          headers=self._headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        applied = 0
        for note in data.get("notes", []):
            self._notes.upsert_remote(self._normalise_note(note))
            applied += 1

        with get_session() as session:
            for tag in data.get("tags", []):
                session.execute(text(
                    "INSERT OR IGNORE INTO tags (id, name, color) "
                    "VALUES (:id, :name, :color)"
                ), tag)
                applied += 1
            for link in data.get("note_tags", []):
                session.execute(text(
                    "INSERT OR IGNORE INTO note_tags (note_id, tag_id) "
                    "VALUES (:note_id, :tag_id)"
                ), link)
                applied += 1
            for link in data.get("note_links", []):
                session.execute(text(
                    "INSERT OR IGNORE INTO note_links "
                    "(source_id, target_id, link_type) "
                    "VALUES (:source_id, :target_id, :link_type)"
                ), link)
                applied += 1

        for pdf in data.get("pdf_assets", []):
            self._upsert_pdf(pdf)
            applied += 1

        return applied

    # ----- upsert 헬퍼 ---------------------------------------------------
    @staticmethod
    def _normalise_note(record: dict) -> dict:
        return {
            "id": record["id"],
            "title": record.get("title", "제목 없음"),
            "body": record.get("body", ""),
            "note_type": record.get("note_type", "IDEA"),
            "is_pinned": record.get("is_pinned", False),
            "color_hint": record.get("color_hint"),
            "created_at": _parse_dt(record.get("created_at")),
            "updated_at": _parse_dt(record.get("updated_at")),
            "deleted_at": _parse_dt(record.get("deleted_at")),
        }

    def _upsert_pdf(self, record: dict) -> None:
        with get_session() as session:
            session.execute(text(
                "INSERT INTO pdf_assets (id, file_path, title, extracted_text, "
                "note_id, created_at, deleted_at) "
                "VALUES (:id, :file_path, :title, :extracted_text, :note_id, "
                ":created_at, :deleted_at) "
                "ON CONFLICT(id) DO UPDATE SET title=excluded.title, "
                "extracted_text=excluded.extracted_text, note_id=excluded.note_id, "
                "deleted_at=excluded.deleted_at"
            ), {
                "id": record["id"],
                "file_path": record.get("file_path", ""),
                "title": record.get("title", ""),
                "extracted_text": record.get("extracted_text"),
                "note_id": record.get("note_id"),
                "created_at": _parse_dt(record.get("created_at")) or datetime.now(),
                "deleted_at": _parse_dt(record.get("deleted_at")),
            })

    # ----- full sync -----------------------------------------------------
    def full_sync(self) -> dict:
        """push → pull 순서로 실행하고 마지막 동기화 시각을 저장한다."""
        self.status_changed.emit("syncing")
        since = self._load_last_sync_at()
        try:
            push_result = self.push_changes(since)
            pulled = self.pull_changes(since)
        except httpx.HTTPError:
            logger.exception("동기화 실패(네트워크 오류)")
            self.status_changed.emit("offline")
            raise

        self._save_last_sync_at(datetime.now())
        result = {
            "pushed": push_result.get("applied", 0),
            "pulled": pulled,
            "conflicts": push_result.get("conflicts", []),
        }
        self.status_changed.emit("online")
        self.sync_completed.emit(result)
        return result

    # ----- 마지막 동기화 시각 저장/로드 ----------------------------------
    @staticmethod
    def _load_last_sync_at() -> datetime | None:
        from config import settings
        return getattr(settings, "LAST_SYNC_AT", None)

    @staticmethod
    def _save_last_sync_at(value: datetime) -> None:
        from config import settings
        settings.LAST_SYNC_AT = value

    # ----- 자동 동기화(QThread) ------------------------------------------
    def start_auto_sync(self, interval_seconds: int = 30) -> None:
        """``interval`` 마다 ``full_sync()`` 를 QThread 에서 호출한다.

        오프라인이면 건너뛴다. UI 블로킹을 막기 위해 별도 스레드에서 실행한다.
        """
        if self._thread is not None:
            return
        self._thread = QThread()
        self._timer = QTimer()
        self._timer.setInterval(max(1, interval_seconds) * 1000)
        self._timer.timeout.connect(self._tick)
        self._timer.moveToThread(self._thread)
        # 스레드가 시작되면 타이머를 가동한다.
        self._thread.started.connect(self._timer.start)
        self._thread.start()

    @Slot()
    def _tick(self) -> None:
        try:
            if self.is_online():
                self.full_sync()
        except Exception:
            logger.exception("자동 동기화 중 오류")

    def stop_auto_sync(self) -> None:
        """자동 동기화 타이머를 중지한다."""
        if self._timer is not None:
            self._timer.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._timer = None

    def run_full_sync_async(self) -> "QThread":
        """수동 "지금 동기화": 단발성 QThread 에서 ``full_sync()`` 를 실행한다."""
        worker = _OneShotSync(self)
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        worker.start()
        return worker


class _OneShotSync(QThread):
    """``full_sync()`` 를 한 번 실행하는 단발성 워커 스레드."""

    def __init__(self, service: SyncService) -> None:
        super().__init__()
        self._service = service

    def run(self) -> None:  # noqa: D401 - QThread 진입점
        try:
            if self._service.is_online():
                self._service.full_sync()
        except Exception:
            logger.exception("수동 동기화 중 오류")


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text_value = str(value).replace("Z", "")
    try:
        return datetime.fromisoformat(text_value)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text_value, fmt)
            except ValueError:
                continue
    return None
