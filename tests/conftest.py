"""Shared pytest fixtures: isolated database per test."""

from __future__ import annotations

import pytest

from db import database


@pytest.fixture()
def db(tmp_path):
    """각 테스트마다 임시 파일 DB로 스키마를 초기화한다."""
    db_path = tmp_path / "test_notes.db"
    database.init_db(db_path)
    yield db_path
    # 전역 엔진 정리.
    if database._engine is not None:
        database._engine.dispose()
    database._engine = None
    database._SessionFactory = None
