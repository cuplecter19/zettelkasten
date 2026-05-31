"""사용자 폰트 업로드/지정 서비스 단위 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.font_service import FONT_TARGETS, FontService, build_css

# 등록 테스트에 사용할 시스템 폰트(없으면 등록 테스트는 건너뛴다).
_SYSTEM_TTF = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _service(tmp_path) -> FontService:
    return FontService(tmp_path / "fonts.json", tmp_path / "fonts")


def test_targets_include_base_and_markdown_elements():
    assert "base" in FONT_TARGETS
    # 기본 텍스트 외에 마크다운 요소도 지정 대상이어야 한다.
    assert "h1" in FONT_TARGETS and "p" in FONT_TARGETS


def test_build_css_emits_rules_only_for_assigned():
    css = build_css({"base": "Foo", "h1": "Bar", "p": ""})
    assert "body { font-family: 'Foo'; }" in css
    assert ".md-h1 { font-family: 'Bar'; }" in css
    # 미지정 요소는 규칙이 없어야 한다.
    assert ".md-p" not in css


def test_set_assignment_persists_and_emits(qtbot, tmp_path):
    svc = _service(tmp_path)
    received = []
    svc.fonts_changed.connect(lambda: received.append(True))
    svc.set_assignment("h1", "Some Family")
    assert received
    assert svc.get_assignment("h1") == "Some Family"
    data = json.loads((tmp_path / "fonts.json").read_text(encoding="utf-8"))
    assert data["assignments"]["h1"] == "Some Family"


def test_set_assignment_empty_clears(tmp_path):
    svc = _service(tmp_path)
    svc.set_assignment("p", "X")
    svc.set_assignment("p", "")
    assert svc.get_assignment("p") == ""
    assert ".md-p" not in svc.build_css()


def test_set_assignment_ignores_unknown_target(tmp_path):
    svc = _service(tmp_path)
    svc.set_assignment("not_a_target", "X")
    assert "not_a_target" not in svc.assignments


def test_reset_clears_assignments(tmp_path):
    svc = _service(tmp_path)
    svc.set_assignment("h1", "X")
    svc.reset()
    assert svc.assignments == {}


def test_add_font_file_rejects_unsupported(tmp_path):
    svc = _service(tmp_path)
    bogus = tmp_path / "not_a_font.txt"
    bogus.write_text("nope", encoding="utf-8")
    assert svc.add_font_file(bogus) is None


@pytest.mark.skipif(not _SYSTEM_TTF.exists(), reason="시스템 폰트 없음")
def test_add_font_file_registers_and_persists(qtbot, tmp_path):
    svc = _service(tmp_path)
    family = svc.add_font_file(_SYSTEM_TTF)
    assert family
    assert family in svc.uploaded_families()
    # 파일이 보관 폴더로 복사되고 설정에 기록된다.
    assert (tmp_path / "fonts").exists()
    data = json.loads((tmp_path / "fonts.json").read_text(encoding="utf-8"))
    assert data["uploaded"]
    # 재로드 시 업로드 폰트가 복원된다.
    reloaded = FontService(tmp_path / "fonts.json", tmp_path / "fonts")
    assert family in reloaded.uploaded_families()
