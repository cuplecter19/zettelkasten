"""연결되지 않은 노트를 주기적으로 수집하는 서비스."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from sqlalchemy import exists, or_, select

from config.settings import APP_DIR
from core.link import NoteLink
from core.note import Note
from db.database import get_session

logger = logging.getLogger(__name__)

ORPHAN_CONFIG_PATH = APP_DIR / "orphan_collector.json"
DEFAULT_INTERVAL_DAYS = 7


class OrphanCollectorService(QObject):
    """링크가 하나도 없는 활성 노트를 수집하고 주간 알림 상태를 저장한다."""

    checked = Signal()

    def __init__(self, path: Path | str = ORPHAN_CONFIG_PATH,
                 interval_days: int = DEFAULT_INTERVAL_DAYS) -> None:
        super().__init__()
        self._path = Path(path)
        self._interval = timedelta(days=max(1, int(interval_days)))
        self._last_checked: date | None = None
        self.load()

    def load(self) -> date | None:
        """마지막 알림 날짜를 읽는다."""
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                value = data.get("last_checked") if isinstance(data, dict) else None
                if isinstance(value, str) and value:
                    self._last_checked = date.fromisoformat(value)
        except (OSError, ValueError):
            logger.exception("orphan_collector.json 로드 실패 — 기본값을 사용합니다.")
        return self._last_checked

    def save(self) -> None:
        """마지막 알림 날짜를 저장한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "last_checked": (
                    self._last_checked.isoformat()
                    if self._last_checked is not None else ""
                )
            }
            self._path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("orphan_collector.json 저장 실패")

    @property
    def last_checked(self) -> date | None:
        return self._last_checked

    def is_due(self, today: date | None = None) -> bool:
        """주간 수집 알림을 띄울 시점인지 반환한다."""
        today = today or date.today()
        if self._last_checked is None:
            return True
        return today - self._last_checked >= self._interval

    def mark_checked(self, today: date | None = None) -> None:
        """이번 주 수집 확인을 완료 처리한다."""
        self._last_checked = today or date.today()
        self.save()
        self.checked.emit()

    def collect_orphans(self) -> list[Note]:
        """들어오거나 나가는 링크가 없는 활성 노트를 최근 수정순으로 반환한다."""
        try:
            with get_session() as session:
                linked = exists().where(
                    or_(NoteLink.source_id == Note.id,
                        NoteLink.target_id == Note.id))
                stmt = (
                    select(Note)
                    .where(Note.deleted_at.is_(None), ~linked)
                    .order_by(Note.updated_at.desc().nullslast(),
                              Note.created_at.desc())
                )
                return list(session.scalars(stmt).all())
        except Exception:
            logger.exception("오펀 노트 수집 실패")
            return []


_service: OrphanCollectorService | None = None


def get_orphan_collector_service() -> OrphanCollectorService:
    """전역 OrphanCollectorService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = OrphanCollectorService()
    return _service
