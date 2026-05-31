"""Phase 1-3: ThemeService 단위 테스트."""

from __future__ import annotations

import json

from services.theme_service import (DEFAULT_THEME, ThemeService,
                                     build_stylesheet)


def test_defaults_loaded(tmp_path):
    svc = ThemeService(tmp_path / "theme.json")
    assert svc.colors == DEFAULT_THEME
    assert svc.get_color("background") == "#ffffff"
    assert svc.get_color("accent") == DEFAULT_THEME["accent"]


def test_save_and_reload_roundtrip(tmp_path):
    path = tmp_path / "theme.json"
    svc = ThemeService(path)
    svc.set_color("background", "#123456")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["background"] == "#123456"

    # 새 인스턴스가 동일 파일에서 값을 복원한다.
    reloaded = ThemeService(path)
    assert reloaded.get_color("background") == "#123456"


def test_set_color_emits_and_updates_stylesheet(qtbot, tmp_path):
    svc = ThemeService(tmp_path / "theme.json")
    received = []
    svc.theme_changed.connect(lambda: received.append(True))
    svc.set_color("accent", "#ff0000")
    assert received  # 시그널 발생
    assert "#ff0000" in svc.build_stylesheet()


def test_set_color_ignores_unknown_key(tmp_path):
    svc = ThemeService(tmp_path / "theme.json")
    svc.set_color("does_not_exist", "#000000")
    assert "does_not_exist" not in svc.colors


def test_get_card_color_falls_back(tmp_path):
    svc = ThemeService(tmp_path / "theme.json")
    assert svc.get_card_color("IDEA") == DEFAULT_THEME["card_IDEA"]
    # 알 수 없는 유형은 안전한 기본값.
    assert svc.get_card_color("UNKNOWN") == "#777777"


def test_reset_restores_defaults(tmp_path):
    svc = ThemeService(tmp_path / "theme.json")
    svc.set_color("text", "#abcdef")
    svc.reset()
    assert svc.colors == DEFAULT_THEME


def test_build_stylesheet_uses_colors():
    qss = build_stylesheet({"background": "#010203", "accent": "#040506"})
    assert "#010203" in qss
    assert "#040506" in qss


def test_build_stylesheet_paints_settings_background():
    qss = build_stylesheet({"background": "#010203"})
    assert "QDialog#SettingsDialog" in qss
    assert "QWidget#SettingsPage" in qss
    assert "QListWidget#SettingsCategoryList" in qss
    assert "QStackedWidget#SettingsStack" in qss
    assert "QWidget { background-color: #010203;" not in qss


def test_build_stylesheet_paints_docked_panels_and_message_boxes():
    qss = build_stylesheet({"background": "#010203", "editor": "#111213"})
    assert "QDockWidget" in qss
    assert "QDockWidget::title" in qss
    assert "QWidget#PDFPanel" in qss
    assert "QWidget#GraphPanel" in qss
    assert "QMessageBox" in qss
    assert "QMessageBox QWidget" in qss
    assert "QGraphicsView" in qss
