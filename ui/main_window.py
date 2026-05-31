"""Main application window: toolbar search, explorer, editor and panels."""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QSplitter, QStyle,
                               QSystemTrayIcon, QToolBar, QVBoxLayout, QWidget)

from db.repositories.note_repo import NoteRepository
from config import settings
from services.export_service import ExportService
from services.linker import LinkerService
from services.sync_service import SyncService
from ui.panels.editor_panel import EditorPanel
from ui.panels.explorer_panel import ExplorerPanel
from ui.panels.graph_panel import GraphPanel
from ui.panels.pdf_panel import PDFPanel
from ui.widgets.quick_capture import HotkeyManager, QuickCaptureDialog

logger = logging.getLogger(__name__)

DARK_STYLESHEET = """
QMainWindow, QWidget { background-color: #1e1e1e; color: #e0e0e0; }
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget {
    background-color: #2a2a2a; color: #e0e0e0; border: 1px solid #3a3a3a;
    border-radius: 4px;
}
QPushButton {
    background-color: #333333; color: #e0e0e0; border: 1px solid #444444;
    border-radius: 4px; padding: 4px 10px;
}
QPushButton:hover { background-color: #3d3d3d; }
QPushButton:checked { background-color: #4A90D9; color: white; }
QToolBar { background-color: #252525; border: none; spacing: 6px; }
QStatusBar { background-color: #252525; }
QMenuBar, QMenu { background-color: #252525; color: #e0e0e0; }
QMenu::item:selected { background-color: #4A90D9; }
"""


class MainWindow(QMainWindow):
    """제텔카스텐 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self._repo = NoteRepository()
        self._linker = LinkerService()
        self._export = ExportService()

        self.setWindowTitle("Zettelkasten")
        self.resize(1100, 720)
        self.setStyleSheet(DARK_STYLESHEET)

        self._build_toolbar()
        self._build_central()
        self._build_menu()
        self._build_docks()
        self._build_statusbar()
        self._setup_tray_and_hotkey()
        self._setup_sync()

        self._refresh_status()

    # ----- UI 구성 --------------------------------------------------------
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("메인", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("검색…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        toolbar.addWidget(self._search)

        new_btn = QPushButton("+ 새 노트", self)
        new_btn.clicked.connect(self._new_note)
        toolbar.addWidget(new_btn)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)

        self._explorer = ExplorerPanel(self)
        self._explorer.note_selected.connect(self._on_note_selected)
        splitter.addWidget(self._explorer)

        right = QSplitter(Qt.Vertical, self)
        self._editor = EditorPanel(self)
        self._editor.note_saved.connect(self._on_note_saved)
        right.addWidget(self._editor)

        # 연결 노트 제안 영역.
        suggestions = QWidget(self)
        sug_layout = QVBoxLayout(suggestions)
        sug_layout.setContentsMargins(4, 4, 4, 4)
        sug_layout.addWidget(QLabel("연결 노트 제안"))
        self._suggestions = QListWidget(suggestions)
        self._suggestions.itemClicked.connect(self._on_suggestion_clicked)
        sug_layout.addWidget(self._suggestions)
        right.addWidget(suggestions)
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일")
        act_md = QAction("노트 Markdown 내보내기", self)
        act_md.triggered.connect(self._export_markdown)
        file_menu.addAction(act_md)
        act_json = QAction("전체 JSON 내보내기", self)
        act_json.triggered.connect(self._export_json)
        file_menu.addAction(act_json)
        act_gexf = QAction("태그 그래프(GEXF) 내보내기", self)
        act_gexf.triggered.connect(self._export_gexf)
        file_menu.addAction(act_gexf)
        file_menu.addSeparator()
        act_sync = QAction("지금 동기화", self)
        act_sync.triggered.connect(self._sync_now)
        file_menu.addAction(act_sync)
        file_menu.addSeparator()
        act_quit = QAction("종료", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        self._view_menu = menubar.addMenu("보기")
        menubar.addMenu("설정")

    def _build_docks(self) -> None:
        self._pdf_panel = PDFPanel(self)
        pdf_dock = QDockWidget("PDF 자산", self)
        pdf_dock.setWidget(self._pdf_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, pdf_dock)
        pdf_dock.hide()
        self._view_menu.addAction(pdf_dock.toggleViewAction())

        self._graph_panel = GraphPanel(self)
        graph_dock = QDockWidget("그래프", self)
        graph_dock.setWidget(self._graph_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, graph_dock)
        graph_dock.hide()
        self._view_menu.addAction(graph_dock.toggleViewAction())

    def _build_statusbar(self) -> None:
        self._status_label = QLabel("", self)
        self.statusBar().addWidget(self._status_label)

        # 동기화 상태 표시(이모지 미사용): 색상 점 + 텍스트.
        self._sync_dot = QLabel(self)
        self._sync_dot.setFixedSize(12, 12)
        self._sync_text = QLabel("오프라인", self)
        self.statusBar().addPermanentWidget(self._sync_dot)
        self.statusBar().addPermanentWidget(self._sync_text)
        self._update_sync_indicator("offline")

    _SYNC_STATES = {
        "online":  ("#3CB371", "연결됨"),
        "offline": ("#C0392B", "오프라인"),
        "syncing": ("#E0A030", "동기화 중"),
    }

    def _update_sync_indicator(self, state: str) -> None:
        color, label = self._SYNC_STATES.get(state, self._SYNC_STATES["offline"])
        # 바닐라 CSS 로 원형 점을 그린다(이모지 대신).
        self._sync_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;")
        self._sync_text.setText(label)

    def _setup_tray_and_hotkey(self) -> None:
        icon = self.style().standardIcon(QStyle.SP_FileDialogListView)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Zettelkasten")
        self._quick = QuickCaptureDialog(self)
        self._quick.note_saved.connect(self._on_quick_saved)

        from PySide6.QtWidgets import QMenu
        tray_menu = QMenu()
        act_capture = QAction("빠른 메모", self)
        act_capture.triggered.connect(self._quick.open_fresh)
        tray_menu.addAction(act_capture)
        act_show = QAction("창 열기", self)
        act_show.triggered.connect(self.showNormal)
        tray_menu.addAction(act_show)
        tray_menu.addSeparator()
        act_exit = QAction("종료", self)
        act_exit.triggered.connect(self.close)
        tray_menu.addAction(act_exit)
        self._tray.setContextMenu(tray_menu)
        try:
            self._tray.show()
        except Exception:
            logger.debug("System tray unavailable", exc_info=True)

        self._hotkey = HotkeyManager()
        self._hotkey.triggered.connect(self._quick.open_fresh)
        self._hotkey.start()

    def _setup_sync(self) -> None:
        """동기화 서비스를 초기화하고, 설정되어 있으면 자동 동기화를 시작한다."""
        self._sync: SyncService | None = None
        try:
            self._sync = SyncService(
                server_url=settings.SYNC_SERVER_URL,
                device_id=settings.DEVICE_ID,
                token=settings.SYNC_TOKEN,
            )
            self._sync.status_changed.connect(self._update_sync_indicator)
            if self._sync_configured():
                self._sync.start_auto_sync(settings.SYNC_INTERVAL)
                self._sync.run_full_sync_async()
        except Exception:
            logger.exception("동기화 초기화 실패 — 로컬 모드로 계속합니다.")

    def _sync_configured(self) -> bool:
        """서버 URL/토큰이 실제 값으로 설정되었는지 확인한다."""
        url = settings.SYNC_SERVER_URL or ""
        return bool(url) and "<" not in url and bool(settings.SYNC_TOKEN)

    def _sync_now(self) -> None:
        """메뉴 "지금 동기화": 백그라운드 스레드에서 즉시 동기화한다."""
        if self._sync is None or not self._sync_configured():
            QMessageBox.information(
                self, "동기화", "동기화 서버가 설정되지 않았습니다.\n"
                "config/settings.py 의 SYNC_SERVER_URL/SYNC_TOKEN 을 확인하세요.")
            return
        self._sync.run_full_sync_async()

    # ----- 동작 -----------------------------------------------------------
    def _on_search(self, text: str) -> None:
        self._explorer.set_query(text)

    def _new_note(self) -> None:
        note = self._repo.create("제목 없음", "", "IDEA")
        self._explorer.refresh()
        self._explorer.select_note(note.id)
        self._on_note_selected(note.id)
        self._refresh_status()

    def _on_note_selected(self, note_id: str) -> None:
        note = self._repo.get_by_id(note_id)
        self._editor.load_note(note)
        self._pdf_panel.set_current_note(note_id)
        self._refresh_suggestions(note_id)

    def _on_note_saved(self, note_id: str) -> None:
        self._explorer.refresh()
        self._explorer.select_note(note_id)
        self._refresh_status()

    def _on_quick_saved(self, note_id: str) -> None:
        self._explorer.refresh()
        self._refresh_status()

    def _refresh_suggestions(self, note_id: str) -> None:
        self._suggestions.clear()
        try:
            for note in self._linker.suggest_links(note_id):
                item = QListWidgetItem(f"{note.title}  ({note.note_type})")
                item.setData(256, note.id)
                self._suggestions.addItem(item)
        except Exception:
            logger.exception("Failed to compute link suggestions")

    def _on_suggestion_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(256)
        if note_id:
            self._explorer.select_note(note_id)
            self._on_note_selected(note_id)

    def _refresh_status(self) -> None:
        count = len(self._repo.list_all())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._status_label.setText(f"노트 {count}개 · 마지막 저장 {now}")

    # ----- 내보내기 -------------------------------------------------------
    def _current_note_id(self) -> str | None:
        return getattr(self._editor, "_current_id", None)

    def _export_markdown(self) -> None:
        note_id = self._current_note_id()
        if note_id is None:
            QMessageBox.information(self, "안내", "먼저 노트를 선택하세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Markdown 저장", "note.md",
                                              "Markdown (*.md)")
        if not path:
            return
        try:
            self._export.export_note_markdown(note_id, path)
        except Exception:
            logger.exception("Markdown export failed")
            QMessageBox.warning(self, "오류", "내보내기에 실패했습니다.")

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "JSON 저장", "notes.json",
                                              "JSON (*.json)")
        if not path:
            return
        try:
            self._export.export_all_json(path)
        except Exception:
            logger.exception("JSON export failed")
            QMessageBox.warning(self, "오류", "내보내기에 실패했습니다.")

    def _export_gexf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "GEXF 저장", "tags.gexf",
                                              "GEXF (*.gexf)")
        if not path:
            return
        try:
            self._export.export_tag_graph_gexf(path)
        except Exception:
            logger.exception("GEXF export failed")
            QMessageBox.warning(self, "오류", "내보내기에 실패했습니다.")

    # ----- 종료 -----------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        try:
            if getattr(self, "_sync", None) is not None and self._sync_configured():
                # 종료 전 마지막 동기화 시도(블로킹 최소화).
                try:
                    if self._sync.is_online():
                        self._sync.full_sync()
                except Exception:
                    logger.debug("종료 시 동기화 실패", exc_info=True)
                self._sync.stop_auto_sync()
        except Exception:
            logger.debug("Sync shutdown failed", exc_info=True)
        try:
            self._hotkey.stop()
        except Exception:
            logger.debug("Hotkey stop failed", exc_info=True)
        super().closeEvent(event)
