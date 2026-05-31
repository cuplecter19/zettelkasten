"""Repository layer for :class:`core.pdf_asset.PdfAsset`."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from core.pdf_asset import PdfAsset, new_uuid
from db.database import get_session

logger = logging.getLogger(__name__)


class PdfRepository:
    """PDF 자산 CRUD 를 담당하는 저장소."""

    def create(self, file_path: str, title: str, thumbnail: bytes | None,
               extracted_text: str | None,
               note_id: str | None = None) -> PdfAsset:
        with get_session() as session:
            asset = PdfAsset(
                id=new_uuid(),
                file_path=file_path,
                title=title,
                thumbnail=thumbnail,
                extracted_text=extracted_text,
                note_id=note_id,
            )
            session.add(asset)
            session.flush()
            session.refresh(asset)
            return asset

    def get_by_id(self, asset_id: str) -> PdfAsset | None:
        with get_session() as session:
            return session.get(PdfAsset, asset_id)

    def list_all(self) -> list[PdfAsset]:
        with get_session() as session:
            stmt = (select(PdfAsset)
                    .where(PdfAsset.deleted_at.is_(None))
                    .order_by(PdfAsset.created_at.desc()))
            return list(session.scalars(stmt).all())

    def delete(self, asset_id: str, device_id: str | None = None) -> None:
        """소프트 삭제: ``deleted_at`` 에 시각을 기록한다."""
        with get_session() as session:
            asset = session.get(PdfAsset, asset_id)
            if asset is not None:
                asset.deleted_at = datetime.now()
                if device_id is not None:
                    asset.last_synced_by = device_id

    def link_to_note(self, asset_id: str, note_id: str | None) -> PdfAsset:
        with get_session() as session:
            asset = session.get(PdfAsset, asset_id)
            if asset is None:
                raise ValueError(f"PdfAsset not found: {asset_id}")
            asset.note_id = note_id
            session.flush()
            session.refresh(asset)
            return asset
