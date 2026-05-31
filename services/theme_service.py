"""UI 색상 테마 관리 서비스.

사용자가 지정한 UI 색상을 ``~/.zettelkasten/theme.json`` 에 저장하고, 전역
``QSS``(Qt Stylesheet)로 변환해 애플리케이션에 적용한다. 색상 변경 시
``theme_changed`` 시그널을 발생시켜 실시간 미리보기를 지원한다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from config.categories import NOTE_TYPE_COLORS
from config.settings import APP_DIR

logger = logging.getLogger(__name__)

THEME_PATH = APP_DIR / "theme.json"

# 커스터마이징 가능한 UI 요소의 기본 색상(다크 테마).
DEFAULT_THEME: dict[str, str] = {
    "background":   "#1e1e1e",
    "sidebar":      "#252525",
    "editor":       "#2a2a2a",
    "text":         "#e0e0e0",
    "accent":       "#4A90D9",
    "card_LEARNING": NOTE_TYPE_COLORS["LEARNING"],
    "card_IDEA":     NOTE_TYPE_COLORS["IDEA"],
    "card_MOOD":     NOTE_TYPE_COLORS["MOOD"],
    "card_ARCHIVE":  NOTE_TYPE_COLORS["ARCHIVE"],
}

# 사람이 읽을 수 있는 라벨(디자인 탭에서 사용).
THEME_LABELS: dict[str, str] = {
    "background":    "배경",
    "sidebar":       "사이드바",
    "editor":        "에디터",
    "text":          "텍스트",
    "accent":        "강조색",
    "card_LEARNING": "노트 카드 · LEARNING",
    "card_IDEA":     "노트 카드 · IDEA",
    "card_MOOD":     "노트 카드 · MOOD",
    "card_ARCHIVE":  "노트 카드 · ARCHIVE",
}


def build_stylesheet(colors: dict[str, str]) -> str:
    """색상 딕셔너리로부터 전역 QSS 문자열을 생성한다."""
    bg = colors.get("background", DEFAULT_THEME["background"])
    sidebar = colors.get("sidebar", DEFAULT_THEME["sidebar"])
    editor = colors.get("editor", DEFAULT_THEME["editor"])
    text = colors.get("text", DEFAULT_THEME["text"])
    accent = colors.get("accent", DEFAULT_THEME["accent"])
    return f"""
QMainWindow, QWidget {{ background-color: {bg}; color: {text}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QListWidget {{
    background-color: {editor}; color: {text}; border: 1px solid #3a3a3a;
    border-radius: 4px;
}}
QPushButton {{
    background-color: {sidebar}; color: {text}; border: 1px solid #444444;
    border-radius: 4px; padding: 4px 10px;
}}
QPushButton:hover {{ background-color: {accent}; }}
QPushButton:checked {{ background-color: {accent}; color: white; }}
QToolBar {{ background-color: {sidebar}; border: none; spacing: 6px; }}
QStatusBar {{ background-color: {sidebar}; }}
QMenuBar, QMenu {{ background-color: {sidebar}; color: {text}; }}
QMenu::item:selected {{ background-color: {accent}; }}
QListWidget::item:selected {{ background-color: {accent}; color: white; }}
"""


class ThemeService(QObject):
    """테마 색상을 로드/저장하고 전역 스타일시트로 적용한다."""

    theme_changed = Signal()

    def __init__(self, path: Path | str = THEME_PATH) -> None:
        super().__init__()
        self._path = Path(path)
        self._colors: dict[str, str] = dict(DEFAULT_THEME)
        self.load()

    # ----- 영속성 ---------------------------------------------------------
    def load(self) -> dict[str, str]:
        """저장된 테마 파일을 읽어 색상을 갱신한다(없으면 기본값 유지)."""
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for key in DEFAULT_THEME:
                        value = data.get(key)
                        if isinstance(value, str) and value:
                            self._colors[key] = value
        except (OSError, ValueError):
            logger.exception("theme.json 로드 실패 — 기본값을 사용합니다.")
        return dict(self._colors)

    def save(self) -> None:
        """현재 색상을 ``theme.json`` 에 기록한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._colors, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("theme.json 저장 실패")

    # ----- 접근자 ---------------------------------------------------------
    @property
    def colors(self) -> dict[str, str]:
        return dict(self._colors)

    def get_color(self, key: str) -> str:
        return self._colors.get(key, DEFAULT_THEME.get(key, "#777777"))

    def get_card_color(self, note_type: str) -> str:
        """노트 유형별 카드 색상(테마 우선, 없으면 기본값)."""
        return self._colors.get(
            f"card_{note_type}", NOTE_TYPE_COLORS.get(note_type, "#777777"))

    def set_color(self, key: str, value: str) -> None:
        """색상 한 항목을 변경하고 저장 후 즉시 적용한다."""
        if key not in DEFAULT_THEME or not value:
            return
        if self._colors.get(key) == value:
            return
        self._colors[key] = value
        self.save()
        self.apply()
        self.theme_changed.emit()

    def reset(self) -> None:
        """기본 테마로 되돌린다."""
        self._colors = dict(DEFAULT_THEME)
        self.save()
        self.apply()
        self.theme_changed.emit()

    # ----- 적용 -----------------------------------------------------------
    def build_stylesheet(self) -> str:
        return build_stylesheet(self._colors)

    def apply(self) -> None:
        """현재 테마를 전역 애플리케이션 스타일시트로 적용한다."""
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(self.build_stylesheet())


_service: ThemeService | None = None


def get_theme_service() -> ThemeService:
    """전역 ThemeService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = ThemeService()
    return _service
