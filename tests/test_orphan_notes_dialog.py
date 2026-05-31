"""연결되지 않은 노트 목록 다이얼로그 테스트."""

from __future__ import annotations

from PySide6.QtCore import Qt

from db.repositories.note_repo import NoteRepository
from ui.dialogs.orphan_notes_dialog import OrphanNotesDialog


def test_orphan_dialog_has_styled_background(qtbot, db):
    note = NoteRepository().create("잊힌 아이디어", "", "IDEA")
    dialog = OrphanNotesDialog([note])
    qtbot.addWidget(dialog)

    assert dialog.objectName() == "OrphanNotesDialog"
    assert dialog.testAttribute(Qt.WA_StyledBackground)
    assert dialog._list.count() == 1
    assert "#fffdf8" not in dialog.styleSheet()


def test_orphan_dialog_emits_requested_note(qtbot, db):
    note = NoteRepository().create("잊힌 아이디어", "", "IDEA")
    dialog = OrphanNotesDialog([note])
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.note_requested) as blocker:
        qtbot.mouseClick(dialog._list.viewport(), Qt.LeftButton)

    assert blocker.args == [note.id]
