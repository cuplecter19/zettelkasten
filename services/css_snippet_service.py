"""Phase 5 — 사용자 정의 CSS 스니펫 서비스.

이름을 가진 CSS 스니펫 목록을 ``~/.zettelkasten/css_snippets.json`` 에 저장하고,
개별 스니펫을 켜고 끌 수 있다. 활성화된 스니펫만 합쳐 마크다운 미리보기의
``extra_css`` 로 사용된다(:mod:`services.markdown_service`). 목록이 바뀌면
``snippets_changed`` 시그널을 발생시켜 실시간 미리보기를 지원한다.

Phase 4 의 :mod:`services.markdown_style_service` 와 독립적으로 동작하며, 두
서비스의 CSS 는 미리보기 단계에서 합쳐진다.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config.settings import APP_DIR

logger = logging.getLogger(__name__)

CSS_SNIPPETS_PATH = APP_DIR / "css_snippets.json"


class CssSnippetService(QObject):
    """이름이 붙은 CSS 스니펫 목록을 로드/저장하고 활성 CSS 로 합친다."""

    snippets_changed = Signal()

    def __init__(self, path: Path | str = CSS_SNIPPETS_PATH) -> None:
        super().__init__()
        self._path = Path(path)
        self._snippets: list[dict] = []
        self.load()

    # ----- 영속성 ---------------------------------------------------------
    def load(self) -> list[dict]:
        """저장된 스니펫 목록을 읽어 갱신한다(없으면 빈 목록)."""
        snippets: list[dict] = []
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        snippet = self._coerce(item)
                        if snippet is not None:
                            snippets.append(snippet)
        except (OSError, ValueError):
            logger.exception("css_snippets.json 로드 실패 — 빈 목록을 사용합니다.")
        self._snippets = snippets
        return self.list_snippets()

    @staticmethod
    def _coerce(item) -> dict | None:
        """저장 데이터를 정규화한 스니펫 dict 로 변환한다(불량 항목은 ``None``)."""
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        css = item.get("css")
        if not isinstance(name, str) or not isinstance(css, str):
            return None
        snippet_id = item.get("id")
        if not isinstance(snippet_id, str) or not snippet_id:
            snippet_id = uuid.uuid4().hex
        return {
            "id": snippet_id,
            "name": name,
            "css": css,
            "enabled": bool(item.get("enabled", True)),
        }

    def save(self) -> None:
        """현재 스니펫 목록을 ``css_snippets.json`` 에 기록한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._snippets, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("css_snippets.json 저장 실패")

    # ----- 접근자 ---------------------------------------------------------
    def list_snippets(self) -> list[dict]:
        return [dict(s) for s in self._snippets]

    def get_snippet(self, snippet_id: str) -> dict | None:
        for snippet in self._snippets:
            if snippet["id"] == snippet_id:
                return dict(snippet)
        return None

    def _find(self, snippet_id: str) -> dict | None:
        for snippet in self._snippets:
            if snippet["id"] == snippet_id:
                return snippet
        return None

    # ----- 변경 -----------------------------------------------------------
    def add_snippet(self, name: str = "새 스니펫", css: str = "") -> str:
        """새 스니펫을 추가하고 그 ``id`` 를 반환한다."""
        snippet = {
            "id": uuid.uuid4().hex,
            "name": name or "새 스니펫",
            "css": css,
            "enabled": True,
        }
        self._snippets.append(snippet)
        self.save()
        self.snippets_changed.emit()
        return snippet["id"]

    def remove_snippet(self, snippet_id: str) -> None:
        snippet = self._find(snippet_id)
        if snippet is None:
            return
        self._snippets.remove(snippet)
        self.save()
        self.snippets_changed.emit()

    def update_snippet(self, snippet_id: str, *, name: str | None = None,
                       css: str | None = None, enabled: bool | None = None) -> None:
        """스니펫의 이름/내용/활성 여부를 변경한다(전달된 값만)."""
        snippet = self._find(snippet_id)
        if snippet is None:
            return
        changed = False
        if name is not None and snippet["name"] != name:
            snippet["name"] = name
            changed = True
        if css is not None and snippet["css"] != css:
            snippet["css"] = css
            changed = True
        if enabled is not None and snippet["enabled"] != bool(enabled):
            snippet["enabled"] = bool(enabled)
            changed = True
        if changed:
            self.save()
            self.snippets_changed.emit()

    # ----- 변환 -----------------------------------------------------------
    def build_css(self) -> str:
        """활성화된 스니펫의 CSS 를 순서대로 합쳐 반환한다."""
        return "\n".join(
            s["css"] for s in self._snippets if s.get("enabled") and s.get("css"))


_service: CssSnippetService | None = None


def get_css_snippet_service() -> CssSnippetService:
    """전역 CssSnippetService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = CssSnippetService()
    return _service
