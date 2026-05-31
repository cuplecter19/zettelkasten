"""Phase 3-1 / 3-3: 에디터 패널 첨부·마크다운 토글 테스트."""

from __future__ import annotations

from db.repositories.note_repo import NoteRepository
from ui.panels.editor_panel import EditorPanel


def test_markdown_toggle_switches_views(qtbot, db):
    note = NoteRepository().create("제목", "# 머리말\n\n본문", "IDEA")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.load_note(note)

    assert panel._body.isVisibleTo(panel)
    panel._md_toggle.setChecked(True)
    assert panel._preview.isVisibleTo(panel)
    assert not panel._body.isVisibleTo(panel)
    # 머리말이 렌더링되어 미리보기에 표시된다.
    assert "머리말" in panel._preview.toPlainText()

    panel._md_toggle.setChecked(False)
    assert panel._body.isVisibleTo(panel)
    assert not panel._preview.isVisibleTo(panel)


def test_insert_image_markdown_appends_link(qtbot, db):
    note = NoteRepository().create("제목", "기존 본문", "IDEA")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.load_note(note)

    panel._insert_image_markdown("/tmp/x/pic.png")
    assert "![](/tmp/x/pic.png)" in panel._body.toPlainText()


def test_loading_note_resets_markdown_toggle(qtbot, db):
    note = NoteRepository().create("제목", "본문", "IDEA")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.load_note(note)
    panel._md_toggle.setChecked(True)

    panel.load_note(note)  # 다시 로드하면 편집 모드로 복귀.
    assert panel._md_toggle.isChecked() is False
