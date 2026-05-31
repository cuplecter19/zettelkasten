"""Phase 5: CSS 스니펫 서비스 테스트."""

from __future__ import annotations

from services.css_snippet_service import CssSnippetService


def _service(tmp_path) -> CssSnippetService:
    return CssSnippetService(tmp_path / "css_snippets.json")


def test_add_snippet_returns_id_and_emits(qtbot, tmp_path):
    service = _service(tmp_path)
    with qtbot.waitSignal(service.snippets_changed):
        snippet_id = service.add_snippet("강조", ".md-h1 { color: red; }")
    assert service.get_snippet(snippet_id)["name"] == "강조"
    assert len(service.list_snippets()) == 1


def test_build_css_only_includes_enabled(tmp_path):
    service = _service(tmp_path)
    on_id = service.add_snippet("on", ".md-h1 { color: red; }")
    off_id = service.add_snippet("off", ".md-h2 { color: blue; }")
    service.update_snippet(off_id, enabled=False)
    css = service.build_css()
    assert ".md-h1 { color: red; }" in css
    assert ".md-h2 { color: blue; }" not in css
    assert on_id and off_id


def test_update_and_remove(qtbot, tmp_path):
    service = _service(tmp_path)
    snippet_id = service.add_snippet("a", "x")
    service.update_snippet(snippet_id, name="b", css=".md-p { margin: 0; }")
    snippet = service.get_snippet(snippet_id)
    assert snippet["name"] == "b"
    assert snippet["css"] == ".md-p { margin: 0; }"
    with qtbot.waitSignal(service.snippets_changed):
        service.remove_snippet(snippet_id)
    assert service.list_snippets() == []


def test_persistence_round_trip(tmp_path):
    service = _service(tmp_path)
    service.add_snippet("keep", ".md-code { font-family: monospace; }")
    reloaded = CssSnippetService(tmp_path / "css_snippets.json")
    snippets = reloaded.list_snippets()
    assert len(snippets) == 1
    assert snippets[0]["name"] == "keep"
    assert snippets[0]["enabled"] is True


def test_load_ignores_malformed_entries(tmp_path):
    path = tmp_path / "css_snippets.json"
    path.write_text(
        '[{"name": "ok", "css": ".a{}"}, "bad", {"name": 5, "css": "x"}]',
        encoding="utf-8")
    service = CssSnippetService(path)
    snippets = service.list_snippets()
    assert len(snippets) == 1
    assert snippets[0]["name"] == "ok"
    assert snippets[0]["id"]
