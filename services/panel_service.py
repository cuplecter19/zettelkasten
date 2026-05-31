"""대시보드 모듈형 패널(패널 모드) 서비스.

대시보드를 구성하는 패널 모듈(요약·유형별 노트 등)의 표시 여부를
``~/.zettelkasten/panels.json`` 에 저장한다. 사용자가 설정의 **패널 모드**
탭에서 각 패널을 켜고 끌 수 있으며, 대시보드 탭은 이 서비스를 참조해 활성화된
패널만 보여준다. 값이 바뀌면 ``panels_changed`` 시그널을 발생시킨다.

다른 설정 서비스와 독립적으로 동작하는 읽기/쓰기 서비스이다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config.settings import APP_DIR

logger = logging.getLogger(__name__)

PANEL_CONFIG_PATH = APP_DIR / "panels.json"

# 대시보드 패널 모듈(키 → 한글 라벨). 표시 순서를 유지한다.
DASHBOARD_PANELS: dict[str, str] = {
    "summary": "요약",
    "by_type": "유형별 노트",
}


class PanelService(QObject):
    """대시보드 패널 모듈의 활성화 상태를 로드/저장한다."""

    panels_changed = Signal()

    def __init__(self, path: Path | str = PANEL_CONFIG_PATH) -> None:
        super().__init__()
        self._path = Path(path)
        # 기본값: 모든 패널 활성화.
        self._enabled: dict[str, bool] = {p: True for p in DASHBOARD_PANELS}
        self.load()

    # ----- 영속성 ---------------------------------------------------------
    def load(self) -> dict[str, bool]:
        """저장된 패널 상태를 읽어 갱신한다(없으면 모두 활성화)."""
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for panel in DASHBOARD_PANELS:
                        value = data.get(panel)
                        if isinstance(value, bool):
                            self._enabled[panel] = value
        except (OSError, ValueError):
            logger.exception("panels.json 로드 실패 — 기본값을 사용합니다.")
        return dict(self._enabled)

    def save(self) -> None:
        """현재 패널 상태를 ``panels.json`` 에 기록한다."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._enabled, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            logger.exception("panels.json 저장 실패")

    # ----- 접근자 ---------------------------------------------------------
    def is_enabled(self, panel: str) -> bool:
        return bool(self._enabled.get(panel, True))

    def enabled_panels(self) -> list[str]:
        """활성화된 패널 키 목록을 정의 순서대로 반환한다."""
        return [p for p in DASHBOARD_PANELS if self.is_enabled(p)]

    def set_enabled(self, panel: str, enabled: bool) -> None:
        """패널의 활성화 여부를 변경하고 저장 후 시그널을 발생시킨다."""
        if panel not in DASHBOARD_PANELS:
            return
        enabled = bool(enabled)
        if self._enabled.get(panel) == enabled:
            return
        self._enabled[panel] = enabled
        self.save()
        self.panels_changed.emit()


_service: PanelService | None = None


def get_panel_service() -> PanelService:
    """전역 PanelService 싱글턴을 반환한다."""
    global _service
    if _service is None:
        _service = PanelService()
    return _service
