"""Phase 3-3: 마크다운 렌더링 서비스 테스트."""

from __future__ import annotations

from services.markdown_service import render_document, render_markdown


def test_headings_get_md_classes():
    html = render_markdown("# 제목\n\n## 소제목")
    assert 'class="md-h1"' in html
    assert 'class="md-h2"' in html


def test_paragraph_and_list_classes():
    html = render_markdown("문단입니다.\n\n- 하나\n- 둘")
    assert 'class="md-p"' in html
    assert 'class="md-ul"' in html
    assert 'class="md-li"' in html


def test_markdown_table_gets_table_cell_classes():
    html = render_markdown("| 제목 | 값 |\n| --- | --- |\n| 하나 | 둘 |")
    assert 'class="md-table"' in html
    assert 'class="md-th"' in html
    assert 'class="md-td"' in html


def test_empty_input_returns_empty():
    assert render_markdown("") == ""


def test_existing_class_preserved_for_links():
    html = render_markdown("[링크](https://example.com)")
    assert "md-a" in html
    assert 'href="https://example.com"' in html


def test_render_document_includes_extra_css():
    doc = render_document("# 안녕", extra_css=".md-h1 { color: red; }")
    assert "<style>" in doc
    assert ".md-h1 { color: red; }" in doc
    assert 'class="md-h1"' in doc
