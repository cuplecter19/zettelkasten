"""Phase 4: 마크다운 서식 설정 서비스 테스트."""

from __future__ import annotations

from services.markdown_style_service import (DEFAULT_MARKDOWN_STYLES,
                                             MarkdownStyleService, build_css)


def _service(tmp_path) -> MarkdownStyleService:
    return MarkdownStyleService(tmp_path / "markdown_style.json")


def test_build_css_targets_md_classes():
    css = build_css(DEFAULT_MARKDOWN_STYLES)
    assert ".md-h1 {" in css
    assert ".md-blockquote {" in css
    assert "font-size:" in css
    assert "color:" in css


def test_default_bold_and_italic_reflected_in_css(tmp_path):
    service = _service(tmp_path)
    css = service.build_css()
    # h1 은 기본 굵게, 인용구는 기본 기울임.
    assert ".md-h1 { font-size: 28px; color: #e0e0e0; font-weight: bold;" in css
    assert "font-style: italic;" in css  # blockquote


def test_set_field_persists_and_emits(qtbot, tmp_path):
    service = _service(tmp_path)
    with qtbot.waitSignal(service.style_changed):
        service.set_field("h1", "font_size", 40)
    assert service.get_style("h1")["font_size"] == 40
    # 새 인스턴스가 같은 파일에서 값을 복원해야 한다.
    reloaded = MarkdownStyleService(tmp_path / "markdown_style.json")
    assert reloaded.get_style("h1")["font_size"] == 40


def test_set_field_rejects_unknown(tmp_path):
    service = _service(tmp_path)
    service.set_field("unknown", "font_size", 99)
    service.set_field("h1", "unknown", 99)
    assert "unknown" not in service.styles


def test_reset_restores_defaults(qtbot, tmp_path):
    service = _service(tmp_path)
    service.set_field("p", "color", "#123456")
    with qtbot.waitSignal(service.style_changed):
        service.reset()
    assert service.get_style("p")["color"] == DEFAULT_MARKDOWN_STYLES["p"]["color"]


def test_color_change_appears_in_css(tmp_path):
    service = _service(tmp_path)
    service.set_field("a", "color", "#ff8800")
    assert ".md-a {" in service.build_css()
    assert "#ff8800" in service.build_css()
