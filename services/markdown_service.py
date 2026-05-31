"""마크다운 → HTML 렌더링 서비스.

``markdown`` 라이브러리로 본문을 HTML 로 변환하고, 각 블록 요소에
``md-<tag>`` 형태의 클래스를 부여한다(예: ``<h1 class="md-h1">``). 이 클래스는
Phase 4 의 마크다운 서식 설정과 CSS 스니펫에서 타깃으로 사용된다.
"""

from __future__ import annotations

import logging
import re

import markdown as _markdown

logger = logging.getLogger(__name__)

# 클래스를 부여할 블록/인라인 요소 목록.
_CLASSED_TAGS = (
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "blockquote", "pre", "code",
    "ul", "ol", "li", "table", "a", "img",
)

# 여는 태그(예: ``<h1>`` 또는 ``<a href="...">``)를 찾는 패턴.
_OPEN_TAG_RE = re.compile(
    r"<(" + "|".join(_CLASSED_TAGS) + r")(\s[^>]*?)?(/?)>",
    re.IGNORECASE,
)


def _inject_classes(html: str) -> str:
    """여는 태그에 ``md-<tag>`` 클래스를 추가한다(기존 class 는 보존)."""

    def repl(match: re.Match) -> str:
        tag = match.group(1).lower()
        attrs = match.group(2) or ""
        self_close = match.group(3) or ""
        cls = f"md-{tag}"
        if re.search(r"\bclass\s*=", attrs, re.IGNORECASE):
            # 기존 class 속성에 덧붙인다.
            attrs = re.sub(
                r'(class\s*=\s*)(["\'])(.*?)\2',
                lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)} {cls}{m.group(2)}',
                attrs, count=1, flags=re.IGNORECASE)
            return f"<{tag}{attrs}{self_close}>"
        return f'<{tag}{attrs} class="{cls}"{self_close}>'

    return _OPEN_TAG_RE.sub(repl, html)


def render_markdown(text: str) -> str:
    """마크다운 문자열을 클래스가 부여된 HTML 로 변환한다."""
    if not text:
        return ""
    try:
        html = _markdown.markdown(
            text, extensions=["fenced_code", "tables", "nl2br"])
    except Exception:
        logger.exception("마크다운 렌더링 실패 — 원문을 그대로 표시합니다.")
        from html import escape
        return f"<pre>{escape(text)}</pre>"
    return _inject_classes(html)


def render_document(text: str, extra_css: str = "") -> str:
    """``<style>`` 를 포함한 완전한 HTML 문서를 반환한다.

    ``extra_css`` 에는 Phase 4 의 마크다운 서식/CSS 스니펫 스타일을 전달한다.
    """
    body = render_markdown(text)
    style = f"<style>{extra_css}</style>" if extra_css else ""
    return f"<html><head>{style}</head><body>{body}</body></html>"
