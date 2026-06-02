"""Phase 3-1 / 3-3: 에디터 패널 첨부·마크다운 토글 테스트."""

from __future__ import annotations

from PySide6.QtGui import QImage

from db.repositories.attachment_repo import AttachmentRepository
from db.repositories.note_repo import NoteRepository
from services.attachment_service import AttachmentService
from services.css_snippet_service import CssSnippetService
from services.markdown_style_service import MarkdownStyleService
from services.theme_service import ThemeService
from ui.panels.editor_panel import CategoryComboBox, EditorPanel, ImageAttachmentCard


def _make_image(path) -> str:
    image = QImage(640, 320, QImage.Format_RGB32)
    image.fill(0x3366FF)
    image.save(str(path), "PNG")
    return str(path)


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


def test_image_attachment_renders_and_deletes(qtbot, db, tmp_path):
    note = NoteRepository().create("제목", "본문", "IDEA")
    svc = AttachmentService(base_dir=tmp_path / "attachments")
    att = svc.add_attachment(note.id, _make_image(tmp_path / "pic.png"))
    panel = EditorPanel()
    panel._attachments = svc
    qtbot.addWidget(panel)
    panel.resize(320, 500)
    panel.load_note(note)
    panel._insert_image_markdown(att.file_path)

    card = panel._attach_layout.itemAt(0).widget()
    assert isinstance(card, ImageAttachmentCard)
    assert card.width() <= panel._body.viewport().width()
    assert not card._delete_btn.isVisible()

    panel._delete_attachment(att.id)

    assert AttachmentRepository().get_by_id(att.id) is None
    assert f"![]({att.file_path})" not in panel._body.toPlainText()


def test_loading_note_resets_markdown_toggle(qtbot, db):
    note = NoteRepository().create("제목", "본문", "IDEA")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.load_note(note)
    panel._md_toggle.setChecked(True)

    panel.load_note(note)  # 다시 로드하면 편집 모드로 복귀.
    assert panel._md_toggle.isChecked() is False


def test_category_dropdown_loads_note_type(qtbot, db):
    note = NoteRepository().create("제목", "본문", "MOOD")
    panel = EditorPanel()
    qtbot.addWidget(panel)

    panel.load_note(note)

    assert panel._category.currentText() == "MOOD"


def test_note_fields_match_search_background_style(qtbot, db, tmp_path):
    panel = EditorPanel()
    panel._theme = ThemeService(tmp_path / "theme.json")
    panel._theme.set_color("editor", "#112233")
    panel._theme.set_color("text", "#445566")
    qtbot.addWidget(panel)

    panel._refresh_editor_field_styles()

    assert "background-color: #112233" in panel._title.styleSheet()
    assert "border-radius: 12px" in panel._title.styleSheet()
    assert "background-color: #112233" in panel._body.styleSheet()
    assert "border-radius: 12px" in panel._body.styleSheet()


def test_category_dropdown_uses_angle_not_svg(qtbot, db, tmp_path):
    panel = EditorPanel()
    panel._theme = ThemeService(tmp_path / "theme.json")
    qtbot.addWidget(panel)

    panel._apply_category_style("IDEA")

    assert isinstance(panel._category, CategoryComboBox)
    assert CategoryComboBox._ANGLE == "\uf107"
    assert CategoryComboBox._ANGLE_AREA_WIDTH == 16
    assert CategoryComboBox._ANGLE_GAP == 4
    assert CategoryComboBox._EXTRA_WIDTH == 30
    assert "data:image/svg+xml" not in panel._category.styleSheet()
    assert "image: none" in panel._category.styleSheet()
    assert "padding: 2px 0px" in panel._category.styleSheet()


def test_category_dropdown_saves_type_and_custom_color(qtbot, db, tmp_path):
    note = NoteRepository().create("제목", "본문", "IDEA")
    panel = EditorPanel()
    panel._theme = ThemeService(tmp_path / "theme.json")
    panel._theme.set_color("card_ARCHIVE", "#123456")
    qtbot.addWidget(panel)
    panel.load_note(note)

    panel._category.setCurrentText("ARCHIVE")

    updated = NoteRepository().get_by_id(note.id)
    assert updated.note_type == "ARCHIVE"
    assert updated.color_hint == "#123456"
    assert "#123456" in panel._category.styleSheet()


def test_preview_applies_markdown_and_snippet_css(qtbot, db, tmp_path):
    """Phase 4/5: 미리보기 HTML 에 서식·스니펫 CSS 가 합쳐져 들어간다."""
    note = NoteRepository().create("제목", "# 머리말", "IDEA")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.load_note(note)

    # 전역 싱글턴을 건드리지 않도록 임시 경로 서비스로 교체.
    panel._css_snippets = CssSnippetService(tmp_path / "css_snippets.json")
    panel._md_style = MarkdownStyleService(tmp_path / "markdown_style.json")
    panel._css_snippets.add_snippet("강조", ".md-h1 { letter-spacing: 2px; }")

    panel._md_toggle.setChecked(True)
    html = panel._preview.toHtml()
    css = panel._markdown_css()
    assert ".md-h1" in css
    assert "letter-spacing: 2px;" in css
    assert "머리말" in html
