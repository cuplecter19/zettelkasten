"""Phase 5 — 설정 다이얼로그의 CSS 스니펫 탭.

사용자 정의 CSS 스니펫을 추가/삭제/편집하고 개별적으로 켜고 끌 수 있다. 변경은
:class:`~services.css_snippet_service.CssSnippetService` 를 통해 즉시 저장되고
``snippets_changed`` 시그널로 미리보기에 반영된다.

서비스 1개만 의존하는 독립 패널로 구성되어, 후속 Phase(대시보드)의 추가와
충돌하지 않는다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from services.css_snippet_service import CssSnippetService


class SettingsCssTab(QWidget):
    """CSS 스니펫 탭: 스니펫 목록 관리 및 편집."""

    def __init__(self, snippets: CssSnippetService, parent=None) -> None:
        super().__init__(parent)
        self._snippets = snippets
        self._current_id: str | None = None

        root = QHBoxLayout(self)

        # 좌측: 스니펫 목록 + 추가/삭제.
        left = QVBoxLayout()
        self._list = QListWidget(self)
        self._list.setFixedWidth(180)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._list.itemChanged.connect(self._on_item_changed)
        left.addWidget(self._list, 1)

        list_buttons = QHBoxLayout()
        self._add_btn = QPushButton("추가", self)
        self._add_btn.clicked.connect(self._add)
        self._remove_btn = QPushButton("삭제", self)
        self._remove_btn.clicked.connect(self._remove)
        list_buttons.addWidget(self._add_btn)
        list_buttons.addWidget(self._remove_btn)
        left.addLayout(list_buttons)
        root.addLayout(left)

        # 우측: 이름 + CSS 편집기.
        right = QVBoxLayout()
        right.addWidget(QLabel("이름", self))
        self._name = QLineEdit(self)
        self._name.setPlaceholderText("스니펫 이름")
        self._name.editingFinished.connect(self._on_name_edited)
        right.addWidget(self._name)

        right.addWidget(QLabel("CSS", self))
        self._editor = QPlainTextEdit(self)
        self._editor.setPlaceholderText(
            ".md-h1 { color: #ff8800; }\n.md-blockquote { border-left: 3px solid #888; }")
        self._editor.textChanged.connect(self._on_css_edited)
        right.addWidget(self._editor, 1)
        root.addLayout(right, 1)

        self._reload()

    # ----- 목록 동기화 ----------------------------------------------------
    def _reload(self) -> None:
        """서비스 상태로 목록을 다시 채운다."""
        self._list.blockSignals(True)
        self._list.clear()
        for snippet in self._snippets.list_snippets():
            item = QListWidgetItem(snippet["name"])
            item.setData(Qt.UserRole, snippet["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if snippet["enabled"] else Qt.Unchecked)
            self._list.addItem(item)
        self._list.blockSignals(False)

        if self._list.count() == 0:
            self._current_id = None
            self._show_editor(False)
            return
        # 이전 선택을 유지하되, 없으면 첫 항목 선택.
        target_row = 0
        for row in range(self._list.count()):
            if self._list.item(row).data(Qt.UserRole) == self._current_id:
                target_row = row
                break
        self._list.setCurrentRow(target_row)

    def _show_editor(self, enabled: bool) -> None:
        self._name.setEnabled(enabled)
        self._editor.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        if not enabled:
            self._name.blockSignals(True)
            self._name.clear()
            self._name.blockSignals(False)
            self._editor.blockSignals(True)
            self._editor.clear()
            self._editor.blockSignals(False)

    # ----- 이벤트 핸들러 --------------------------------------------------
    def _on_selection_changed(self, current: QListWidgetItem | None,
                              _previous: QListWidgetItem | None = None) -> None:
        if current is None:
            self._current_id = None
            self._show_editor(False)
            return
        self._current_id = current.data(Qt.UserRole)
        snippet = self._snippets.get_snippet(self._current_id)
        if snippet is None:
            self._show_editor(False)
            return
        self._show_editor(True)
        self._name.blockSignals(True)
        self._name.setText(snippet["name"])
        self._name.blockSignals(False)
        self._editor.blockSignals(True)
        self._editor.setPlainText(snippet["css"])
        self._editor.blockSignals(False)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """체크 상태(활성 여부) 변경을 서비스에 반영한다."""
        snippet_id = item.data(Qt.UserRole)
        if snippet_id is None:
            return
        self._snippets.update_snippet(
            snippet_id, enabled=item.checkState() == Qt.Checked)

    def _on_name_edited(self) -> None:
        if self._current_id is None:
            return
        name = self._name.text().strip() or "새 스니펫"
        self._snippets.update_snippet(self._current_id, name=name)
        # 목록 라벨을 갱신.
        item = self._list.currentItem()
        if item is not None:
            item.setText(name)

    def _on_css_edited(self) -> None:
        if self._current_id is None:
            return
        self._snippets.update_snippet(
            self._current_id, css=self._editor.toPlainText())

    def _add(self) -> None:
        self._current_id = self._snippets.add_snippet()
        self._reload()
        self._name.setFocus()

    def _remove(self) -> None:
        if self._current_id is None:
            return
        self._snippets.remove_snippet(self._current_id)
        self._current_id = None
        self._reload()


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    from services.css_snippet_service import CssSnippetService

    app = QApplication(sys.argv)
    widget = SettingsCssTab(CssSnippetService())
    widget.resize(640, 400)
    widget.show()
    sys.exit(app.exec())
