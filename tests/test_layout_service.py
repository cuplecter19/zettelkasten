"""Phase 2-1: 레이아웃(스플리터 너비) 영속화 테스트."""

from __future__ import annotations

from services.layout_service import LayoutService


def test_set_and_get_sizes_roundtrip(tmp_path):
    svc = LayoutService(tmp_path / "layout.json")
    svc.set_sizes("central_splitter", [300, 700])
    assert svc.get_sizes("central_splitter") == [300, 700]


def test_sizes_persist_across_instances(tmp_path):
    path = tmp_path / "layout.json"
    LayoutService(path).set_sizes("right_splitter", [400, 200])
    reloaded = LayoutService(path)
    assert reloaded.get_sizes("right_splitter") == [400, 200]


def test_missing_key_returns_none(tmp_path):
    svc = LayoutService(tmp_path / "layout.json")
    assert svc.get_sizes("nope") is None


def test_corrupt_file_falls_back(tmp_path):
    path = tmp_path / "layout.json"
    path.write_text("{ not valid json", encoding="utf-8")
    svc = LayoutService(path)  # 예외 없이 빈 상태로 시작.
    assert svc.get_sizes("central_splitter") is None
