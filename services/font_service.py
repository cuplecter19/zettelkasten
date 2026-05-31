"""사용자 폰트 업로드 및 요소별 폰트 지정 서비스.

사용자가 직접 업로드한 폰트 파일(``.ttf``/``.otf``/``.ttc``)을
``~/.zettelkasten/fonts/`` 에 복사하고 ``QFontDatabase`` 에 등록한다. 등록된
폰트(또는 시스템 폰트)를 **기본 텍스트** 및 **마크다운 요소별**로 지정할 수
있으며, 지정 결과는 마크다운 미리보기의 ``extra_css`` 로 변환되어
:mod:`services.markdown_service` 의 렌더링에 적용된다.

다른 설정 서비스(:mod:`services.markdown_style_service`,
:mod:`services.css_snippet_service`)와 독립적으로 동작하며, 폰트 CSS 는
미리보기 단계에서 함께 합쳐진다. 값이 바뀌면 ``fonts_changed`` 시그널을
발생시켜 실시간 미리보기를 지원한다.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFontDatabase

from config.settings import APP_DIR
from services.markdown_style_service import MARKDOWN_ELEMENTS, MARKDOWN_SELECTORS

logger = logging.getLogger(__name__)

FONTS_DIR = APP_DIR / "fonts"
FONT_CONFIG_PATH = APP_DIR / "fonts.json"

# 폰트를 지정할 수 있는 대상(키 → 한글 라벨).
# "base" 는 미리보기 본문 전체(기본 텍스트), 나머지는 마크다운 요소별 폰트.
FONT_TARGETS: dict[str, str] = {"base": "기본 텍스트", **MARKDOWN_ELEMENTS}

# CSS 선택자 매핑(base 는 body 전체).
_TARGET_SELECTORS: dict[str, str] = {
    "base": "body",
    **MARKDOWN_SELECTORS,
}

# 지원하는 폰트 파일 확장자.
SUPPORTED_FONT_SUFFIXES = (".ttf", ".otf", ".ttc")


def build_css(assignments: dict[str, str]) -> str:
    """대상별 폰트 패밀리 매핑을 ``font-family`` CSS 로 변환한다.

    빈 문자열(미지정)인 대상은 규칙을 생성하지 않아 상속 동작을 유지한다.
    """
    rules: list[str] = []
    for target, selector in _TARGET_SELECTORS.items():
        family = assignments.get(target, "")
        if isinstance(family, str) and family:
            rules.append(f"{selector} {{ font-family: '{family}'; }}")
    return "\n".join(rules)


class FontService(QObject):
    """업로드 폰트를 등록하고 요소별 폰트 지정을 관리한다."""

    fonts_changed = Signal()

    def __init__(self, path: Path | str = FONT_CONFIG_PATH,
                 fonts_dir: Path | str = FONTS_DIR) -> None:
        super().__init__()
        self._path = Path(path)
        self._fonts_dir = Path(fonts_dir)
        # 업로드된 폰트: [{"id", "path", "family"}].
        self._uploaded: list[dict] = []
        # 대상별 폰트 패밀리 지정: {target: family}.
        self._assignments: dict[str, str] = {}
        self.load()

    # ----- 영속성 ---------------------------------------------------------
    def load(self) -> None:
        """저장된 설정을 읽고 업로드 폰트를 ``QFontDatabase`` 에 등록한다."""
        self._uploaded = []
        self._assignments = {}
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._load_uploaded(data.get("uploaded"))
                    self._load_assignments(data.get("assignments"))
        except (OSError, ValueError):
            logger.exception("fonts.json 로드 실패 — 기본값을 사용합니다.")

    def _load_uploaded(self, items) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if not isinstance(path, str) or not Path(path).exists():
                continue
            family = self._register_font_file(path)
            if not family:
                continue
            self._uploaded.append({
                "id": item.get("id") or uuid.uuid4().hex,
                "path": path,
                "family": family,
            })

    def _load_assignments(self, items) -> None:
        if not isinstance(items, dict):
            return
        for target, family in items.items():
            if target in FONT_TARGETS and isinstance(family, str):
                self._assignments[target] = family

    def save(self) -> None:
        """현재 설정을 ``fonts.json`` 에 기록한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "uploaded": self._uploaded,
                "assignments": self._assignments,
            }
            self._path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("fonts.json 저장 실패")

    # ----- 폰트 등록 ------------------------------------------------------
    @staticmethod
    def _register_font_file(path: str) -> str | None:
        """폰트 파일을 ``QFontDatabase`` 에 등록하고 패밀리명을 반환한다."""
        try:
            font_id = QFontDatabase.addApplicationFont(path)
        except Exception:
            logger.exception("폰트 등록 실패: %s", path)
            return None
        if font_id == -1:
            logger.warning("폰트를 등록할 수 없습니다: %s", path)
            return None
        families = QFontDatabase.applicationFontFamilies(font_id)
        return families[0] if families else None

    def add_font_file(self, source_path: str | Path) -> str | None:
        """폰트 파일을 보관 폴더로 복사·등록하고 패밀리명을 반환한다.

        등록에 실패하거나 지원하지 않는 형식이면 ``None`` 을 반환한다.
        """
        source = Path(source_path)
        if source.suffix.lower() not in SUPPORTED_FONT_SUFFIXES:
            logger.warning("지원하지 않는 폰트 형식: %s", source)
            return None
        try:
            self._fonts_dir.mkdir(parents=True, exist_ok=True)
            dest = self._fonts_dir / f"{uuid.uuid4().hex}{source.suffix.lower()}"
            shutil.copyfile(source, dest)
        except OSError:
            logger.exception("폰트 파일 복사 실패: %s", source)
            return None

        family = self._register_font_file(str(dest))
        if not family:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                logger.debug("등록 실패 폰트 정리 실패", exc_info=True)
            return None

        self._uploaded.append({
            "id": uuid.uuid4().hex, "path": str(dest), "family": family})
        self.save()
        self.fonts_changed.emit()
        return family

    # ----- 접근자 ---------------------------------------------------------
    def uploaded_families(self) -> list[str]:
        """업로드된 폰트 패밀리 목록(중복 제거, 등록 순서 유지)."""
        seen: list[str] = []
        for item in self._uploaded:
            family = item.get("family")
            if family and family not in seen:
                seen.append(family)
        return seen

    def available_families(self) -> list[str]:
        """지정에 사용할 수 있는 전체 폰트 패밀리(업로드 + 시스템)."""
        families = self.uploaded_families()
        try:
            system = list(QFontDatabase.families())
        except Exception:
            system = []
        for family in system:
            if family not in families:
                families.append(family)
        return families

    @property
    def assignments(self) -> dict[str, str]:
        return dict(self._assignments)

    def get_assignment(self, target: str) -> str:
        return self._assignments.get(target, "")

    def set_assignment(self, target: str, family: str) -> None:
        """대상의 폰트 패밀리를 지정한다(빈 문자열이면 지정 해제)."""
        if target not in FONT_TARGETS:
            return
        family = family or ""
        if self._assignments.get(target, "") == family:
            return
        if family:
            self._assignments[target] = family
        else:
            self._assignments.pop(target, None)
        self.save()
        self.fonts_changed.emit()

    def reset(self) -> None:
        """폰트 지정을 모두 해제한다(업로드 폰트는 유지)."""
        if not self._assignments:
            return
        self._assignments = {}
        self.save()
        self.fonts_changed.emit()

    # ----- 변환 -----------------------------------------------------------
    def build_css(self) -> str:
        return build_css(self._assignments)


_service: FontService | None = None


def get_font_service() -> FontService:
    """전역 FontService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = FontService()
    return _service
