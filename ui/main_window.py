"""Main application window: toolbar search, explorer, editor and panels."""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow,
                               QMenuBar, QMessageBox, QPushButton, QSplitter,
                               QSizePolicy, QStyle, QSystemTrayIcon, QToolBar,
                               QVBoxLayout, QWidget)

from db.repositories.note_repo import NoteRepository
from config import settings
from services.export_service import ExportService
from services.dashboard_service import get_dashboard_service
from services.linker import LinkerService
from services.layout_service import LayoutService
from services.orphan_service import get_orphan_collector_service
from services.sync_service import SyncService
from services.theme_service import get_theme_service
from ui.dialogs.orphan_notes_dialog import OrphanNotesDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.panels.editor_panel import EditorPanel
from ui.panels.explorer_panel import ExplorerPanel
from ui.panels.graph_panel import GraphPanel
from ui.panels.pdf_panel import PDFPanel
from ui.widgets.quick_capture import HotkeyManager, QuickCaptureDialog
from ui.widgets.startup_dashboard import StartupDashboardOverlay
from ui.widgets.title_bar import CustomTitleBar, FramelessResizer

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """제텔카스텐 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self._repo = NoteRepository()
        self._linker = LinkerService()
        self._export = ExportService()
        self._theme = get_theme_service()
        self._dashboard = get_dashboard_service()
        self._orphans = get_orphan_collector_service()
        self._layout = LayoutService()

        self.setWindowTitle("Zettelkasten")
        self.resize(1100, 720)

        # 기본 제목 표시줄 제거(커스텀 타이틀바 사용).
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self._apply_theme()
        self._theme.theme_changed.connect(self._apply_theme)

        self._build_toolbar()
        self._build_central()
        self._build_menu()
        self._build_titlebar()
        self._build_docks()
        self._build_statusbar()
        self._setup_tray_and_hotkey()
        self._setup_sync()
        self._build_startup_dashboard()

        # 프레임리스 창 가장자리 리사이즈 핸들.
        self._resizer = FramelessResizer(self)
        self._resizer.reposition()

        self._refresh_status()
        QTimer.singleShot(0, self._show_weekly_orphans)

    def _apply_theme(self) -> None:
        """현재 테마를 창에 적용한다."""
        self.setStyleSheet(self._theme.build_stylesheet())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._apply_rounded_mask()
        if getattr(self, "_resizer", None) is not None:
            self._resizer.reposition()
        if getattr(self, "_startup_dashboard", None) is not None:
            self._startup_dashboard.setGeometry(self.rect())

    def _apply_rounded_mask(self) -> None:
        """프레임리스 창의 네 모서리를 둥글게 잘라낸다."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainterPath, QRegion

        if self.isMaximized():
            self.clearMask()
            return
        radius = 24
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    # ----- UI 구성 --------------------------------------------------------
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("메인", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("검색")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(520)
        self._search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._search.textChanged.connect(self._on_search)
        toolbar.addWidget(self._search)

        new_btn = QPushButton("+ 새 노트", self)
        new_btn.clicked.connect(self._new_note)
        toolbar.addWidget(new_btn)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)
        self._central_splitter = splitter

        self._explorer = ExplorerPanel(self)
        self._explorer.note_selected.connect(self._on_note_selected)
        self._explorer.note_deleted.connect(self._on_note_deleted)
        splitter.addWidget(self._explorer)

        right = QSplitter(Qt.Vertical, self)
        self._right_splitter = right
        self._editor = EditorPanel(self)
        self._editor.note_saved.connect(self._on_note_saved)
        self._editor.attachment_added.connect(self._on_attachment_added)
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

        # 저장된 패널 너비를 복원하고, 이동 시 저장한다.
        self._restore_splitter_sizes()
        splitter.splitterMoved.connect(
            lambda *_: self._layout.set_sizes(
                "central_splitter", splitter.sizes()))
        right.splitterMoved.connect(
            lambda *_: self._layout.set_sizes(
                "right_splitter", right.sizes()))

    def _restore_splitter_sizes(self) -> None:
        central = self._layout.get_sizes("central_splitter")
        if central:
            self._central_splitter.setSizes(central)
        right = self._layout.get_sizes("right_splitter")
        if right:
            self._right_splitter.setSizes(right)

    def _build_menu(self) -> None:
        menubar = QMenuBar(self)
        self._menubar = menubar

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
        act_orphans = QAction("연결 안 된 아이디어 보기", self)
        act_orphans.triggered.connect(lambda: self._show_orphans(mark_checked=False))
        self._view_menu.addAction(act_orphans)

        settings_menu = menubar.addMenu("설정")
        act_settings = QAction("설정…", self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.triggered.connect(self._open_settings)
        settings_menu.addAction(act_settings)
        # 단축키가 메뉴를 열지 않아도 동작하도록 창에도 등록.
        self.addAction(act_settings)

    def _build_titlebar(self) -> None:
        """커스텀 타이틀바와 메뉴바를 위아래로 분리해 창 상단에 배치한다."""
        header = QWidget(self)
        header.setObjectName("WindowHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._title_bar = CustomTitleBar(self, title="")
        header_layout.addWidget(self._title_bar)
        header_layout.addWidget(self._menubar)
        self.setMenuWidget(header)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, theme=self._theme)
        dialog.exec()

    def _build_startup_dashboard(self) -> None:
        """설정된 색상/이미지로 첫 화면 오버레이를 올린다."""
        self._startup_dashboard = StartupDashboardOverlay(
            self._dashboard.welcome_color(),
            self._dashboard.welcome_image_path(),
            self,
        )
        self._startup_dashboard.setGeometry(self.rect())
        self._startup_dashboard.raise_()
        self._startup_dashboard.show()


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
        self.statusBar().setContentsMargins(12, 0, 12, 0)
        self._status_label = QLabel("", self)
        self._status_label.setContentsMargins(12, 0, 0, 0)
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

    def _on_attachment_added(self, note_id: str) -> None:
        """첨부/썸네일 변경 시 리스트 카드 미디어를 갱신한다."""
        self._explorer.refresh()
        self._explorer.select_note(note_id)

    def _on_note_deleted(self, note_id: str) -> None:
        """노트가 삭제되면 편집 중이던 노트를 비우고 상태를 갱신한다."""
        if self._current_note_id() == note_id:
            self._editor.load_note(None)
            self._suggestions.clear()
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

    def _show_weekly_orphans(self) -> None:
        if self._orphans.is_due():
            self._show_orphans(mark_checked=True)

    def _show_orphans(self, mark_checked: bool = True) -> None:
        notes = self._orphans.collect_orphans()
        if mark_checked:
            self._orphans.mark_checked()
        if not notes:
            return
        self._orphan_dialog = OrphanNotesDialog(notes, self)
        self._orphan_dialog.note_requested.connect(self._open_orphan_note)
        self._orphan_dialog.show()
        self._orphan_dialog.raise_()
        self._orphan_dialog.activateWindow()

    def _open_orphan_note(self, note_id: str) -> None:
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
