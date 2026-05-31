"""레이아웃(스플리터 너비 등) 영속화 서비스.

메인 윈도우의 패널 분할 너비를 ``~/.zettelkasten/layout.json`` 에 저장하고
다음 실행 시 복원한다. 인지 부하를 줄이기 위해 사용자가 마지막으로 맞춘
레이아웃을 그대로 유지한다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config.settings import APP_DIR

logger = logging.getLogger(__name__)

LAYOUT_PATH = APP_DIR / "layout.json"


class LayoutService:
    """이름표가 붙은 레이아웃 값을 JSON 파일로 저장/복원한다."""

    def __init__(self, path: Path | str = LAYOUT_PATH) -> None:
        self._path = Path(path)
        self._data: dict[str, object] = {}
        self.load()

    def load(self) -> dict[str, object]:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._data = data
        except (OSError, ValueError):
            logger.exception("layout.json 로드 실패 — 기본 레이아웃을 사용합니다.")
        return dict(self._data)

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("layout.json 저장 실패")

    # ----- 스플리터 헬퍼 ---------------------------------------------------
    def get_sizes(self, key: str) -> list[int] | None:
        """저장된 스플리터 크기 목록을 반환한다(없으면 ``None``)."""
        value = self._data.get(key)
        if isinstance(value, list) and all(isinstance(v, int) for v in value):
            return list(value)
        return None

    def set_sizes(self, key: str, sizes: list[int]) -> None:
        """스플리터 크기 목록을 저장(파일에 즉시 기록)한다."""
        self._data[key] = [int(v) for v in sizes]
        self.save()
