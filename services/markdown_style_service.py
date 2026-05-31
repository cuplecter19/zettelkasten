"""Phase 4 — 마크다운 서식 설정 서비스.

마크다운 미리보기의 각 요소(제목·본문·인용구 등)별 글꼴 크기/색상/굵기/기울임을
``~/.zettelkasten/markdown_style.json`` 에 저장하고, ``markdown_service`` 가
부여하는 ``md-<tag>`` 클래스를 타깃으로 하는 CSS 로 변환한다. 값이 바뀌면
``style_changed`` 시그널을 발생시켜 실시간 미리보기를 지원한다.

이 서비스는 :mod:`services.css_snippet_service` (Phase 5) 와 독립적으로 동작하며,
:func:`build_css` 결과는 ``markdown_service.render_document`` 의 ``extra_css`` 로
전달된다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config.settings import APP_DIR
from services.theme_service import DEFAULT_THEME

logger = logging.getLogger(__name__)

MARKDOWN_STYLE_PATH = APP_DIR / "markdown_style.json"

# 사용자에게 노출하는 마크다운 요소(클래스 ``md-<key>``)와 한글 라벨.
MARKDOWN_ELEMENTS: dict[str, str] = {
    "h1":         "제목 1",
    "h2":         "제목 2",
    "h3":         "제목 3",
    "p":          "본문",
    "ul":         "리스트",
    "blockquote": "인용구",
    "code":       "코드",
    "table":      "테이블",
    "th":         "테이블 헤더",
    "td":         "테이블 내용",
    "a":          "링크",
}

MARKDOWN_SELECTORS: dict[str, str] = {
    "ul": ".md-ul, .md-ol, .md-li",
    **{element: f".md-{element}" for element in MARKDOWN_ELEMENTS if element != "ul"},
}

# 편집 가능한 서식 필드와 기본 검증.
_FIELDS = ("font_size", "color", "bold", "italic")

# 요소별 기본 서식(다크 테마 기준).
DEFAULT_MARKDOWN_STYLES: dict[str, dict] = {
    "h1":         {"font_size": 28, "color": DEFAULT_THEME["text"], "bold": True,  "italic": False},
    "h2":         {"font_size": 24, "color": DEFAULT_THEME["text"], "bold": True,  "italic": False},
    "h3":         {"font_size": 20, "color": DEFAULT_THEME["text"], "bold": True,  "italic": False},
    "p":          {"font_size": 14, "color": DEFAULT_THEME["text"], "bold": False, "italic": False},
    "ul":         {"font_size": 14, "color": DEFAULT_THEME["text"], "bold": False, "italic": False},
    "blockquote": {"font_size": 14, "color": "#a0a0a0", "bold": False, "italic": True},
    "code":       {"font_size": 13, "color": "#d7ba7d", "bold": False, "italic": False},
    "table":      {"font_size": 14, "color": DEFAULT_THEME["text"], "bold": False, "italic": False},
    "th":         {"font_size": 14, "color": DEFAULT_THEME["text"], "bold": True,  "italic": False},
    "td":         {"font_size": 14, "color": DEFAULT_THEME["text"], "bold": False, "italic": False},
    "a":          {"font_size": 14, "color": "#4a90d9", "bold": False, "italic": False},
}


def _default_styles() -> dict[str, dict]:
    """기본 서식의 깊은 복사본을 반환한다."""
    return {el: dict(style) for el, style in DEFAULT_MARKDOWN_STYLES.items()}


def build_css(styles: dict[str, dict]) -> str:
    """요소별 서식 딕셔너리를 ``.md-<tag>`` 선택자 CSS 로 변환한다."""
    rules: list[str] = []
    for element, style in styles.items():
        font_size = style.get("font_size",
                               DEFAULT_MARKDOWN_STYLES.get(element, {}).get("font_size", 14))
        color = style.get("color",
                          DEFAULT_MARKDOWN_STYLES.get(element, {}).get("color", "#e0e0e0"))
        weight = "bold" if style.get("bold") else "normal"
        font_style = "italic" if style.get("italic") else "normal"
        decls = (
            f"font-size: {int(font_size)}px; "
            f"color: {color}; "
            f"font-weight: {weight}; "
            f"font-style: {font_style};"
        )
        selector = MARKDOWN_SELECTORS.get(element, f".md-{element}")
        rules.append(f"{selector} {{ {decls} }}")
    return "\n".join(rules)


class MarkdownStyleService(QObject):
    """마크다운 요소별 서식을 로드/저장하고 CSS 로 변환한다."""

    style_changed = Signal()

    def __init__(self, path: Path | str = MARKDOWN_STYLE_PATH) -> None:
        super().__init__()
        self._path = Path(path)
        self._styles = _default_styles()
        self.load()

    # ----- 영속성 ---------------------------------------------------------
    def load(self) -> dict[str, dict]:
        """저장된 서식 파일을 읽어 갱신한다(없으면 기본값 유지)."""
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for element in DEFAULT_MARKDOWN_STYLES:
                        saved = data.get(element)
                        if isinstance(saved, dict):
                            self._merge_element(element, saved)
        except (OSError, ValueError):
            logger.exception("markdown_style.json 로드 실패 — 기본값을 사용합니다.")
        return self.styles

    def _merge_element(self, element: str, saved: dict) -> None:
        target = self._styles[element]
        if isinstance(saved.get("font_size"), int):
            target["font_size"] = saved["font_size"]
        if isinstance(saved.get("color"), str) and saved["color"]:
            target["color"] = saved["color"]
        if isinstance(saved.get("bold"), bool):
            target["bold"] = saved["bold"]
        if isinstance(saved.get("italic"), bool):
            target["italic"] = saved["italic"]

    def save(self) -> None:
        """현재 서식을 ``markdown_style.json`` 에 기록한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._styles, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("markdown_style.json 저장 실패")

    # ----- 접근자 ---------------------------------------------------------
    @property
    def styles(self) -> dict[str, dict]:
        return {el: dict(style) for el, style in self._styles.items()}

    def get_style(self, element: str) -> dict:
        return dict(self._styles.get(element, {}))

    def set_field(self, element: str, field: str, value) -> None:
        """한 요소의 서식 필드를 변경하고 저장 후 시그널을 발생시킨다."""
        if element not in self._styles or field not in _FIELDS:
            return
        if field == "font_size":
            try:
                value = int(value)
            except (TypeError, ValueError):
                return
        elif field == "color":
            if not isinstance(value, str) or not value:
                return
        else:  # bold / italic
            value = bool(value)
        if self._styles[element].get(field) == value:
            return
        self._styles[element][field] = value
        self.save()
        self.style_changed.emit()

    def reset(self) -> None:
        """기본 서식으로 되돌린다."""
        self._styles = _default_styles()
        self.save()
        self.style_changed.emit()

    # ----- 변환 -----------------------------------------------------------
    def build_css(self) -> str:
        return build_css(self._styles)


_service: MarkdownStyleService | None = None


def get_markdown_style_service() -> MarkdownStyleService:
    """전역 MarkdownStyleService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = MarkdownStyleService()
    return _service
