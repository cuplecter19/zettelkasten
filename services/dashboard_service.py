"""Phase 6 — 대시보드(통계 요약) 서비스.

로컬 DB 에서 노트/태그/링크/첨부 등의 집계 통계를 읽어 대시보드 탭에 제공한다.
읽기 전용 서비스로, 데이터를 변경하지 않으므로 다른 Phase(디자인·마크다운·CSS
스니펫)의 서비스와 충돌하지 않는다. DB 가 아직 초기화되지 않았거나 조회에
실패하면 0 으로 채운 기본 통계를 돌려주어 단독 실행/테스트에서도 안전하다.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from sqlalchemy import func, select

from core.note import Note
from core.tag import Tag, note_tags
from db.database import get_session

logger = logging.getLogger(__name__)

# 노트 유형(스키마 CHECK 제약과 동일한 순서)과 한글 라벨.
NOTE_TYPE_LABELS: dict[str, str] = {
    "LEARNING": "학습",
    "IDEA":     "아이디어",
    "MOOD":     "감정",
    "ARCHIVE":  "보관",
}


def _empty_stats() -> dict:
    """DB 조회 실패 시 사용할 0 채움 통계."""
    return {
        "total_notes": 0,
        "pinned_notes": 0,
        "by_type": {note_type: 0 for note_type in NOTE_TYPE_LABELS},
        "total_tags": 0,
        "total_links": 0,
        "total_attachments": 0,
        "total_pdf_assets": 0,
        "untagged_notes": 0,
    }


class DashboardService(QObject):
    """로컬 DB 의 집계 통계를 수집하는 읽기 전용 서비스."""

    stats_changed = Signal()

    def collect_stats(self) -> dict:
        """현재 DB 상태의 통계 딕셔너리를 반환한다.

        삭제된(소프트 삭제) 노트는 제외한다. 어떤 이유로든 조회에 실패하면
        :func:`_empty_stats` 를 반환해 호출 측이 항상 동일한 형태를 받도록 한다.
        """
        stats = _empty_stats()
        try:
            with get_session() as session:
                active = Note.deleted_at.is_(None)

                stats["total_notes"] = int(
                    session.scalar(
                        select(func.count()).select_from(Note).where(active))
                    or 0)
                stats["pinned_notes"] = int(
                    session.scalar(
                        select(func.count()).select_from(Note)
                        .where(active, Note.is_pinned.is_(True)))
                    or 0)

                by_type = dict(stats["by_type"])
                rows = session.execute(
                    select(Note.note_type, func.count())
                    .where(active)
                    .group_by(Note.note_type))
                for note_type, count in rows:
                    if note_type in by_type:
                        by_type[note_type] = int(count)
                stats["by_type"] = by_type

                stats["total_tags"] = int(
                    session.scalar(select(func.count()).select_from(Tag)) or 0)

                # 활성 노트 중 태그가 하나도 없는 노트 수.
                tagged = select(note_tags.c.note_id).distinct().subquery()
                stats["untagged_notes"] = int(
                    session.scalar(
                        select(func.count()).select_from(Note)
                        .where(active, Note.id.not_in(select(tagged.c.note_id))))
                    or 0)

                stats["total_links"] = _count_table(session, "note_links")
                stats["total_attachments"] = _count_table(session, "attachments")
                stats["total_pdf_assets"] = _count_table(session, "pdf_assets")
        except Exception:
            logger.exception("대시보드 통계 수집 실패 — 빈 통계를 사용합니다.")
            return _empty_stats()
        return stats


def _count_table(session, table: str) -> int:
    """단순 테이블 행 수를 센다(없거나 실패하면 0)."""
    from sqlalchemy import text

    try:
        result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        return int(result or 0)
    except Exception:
        logger.debug("%s 테이블 집계 실패", table, exc_info=True)
        return 0


_service: DashboardService | None = None


def get_dashboard_service() -> DashboardService:
    """전역 DashboardService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = DashboardService()
    return _service
