"""Graph panel: visualize the note-tag graph with QGraphicsScene."""

from __future__ import annotations

import logging

import networkx as nx
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsScene,
                               QGraphicsView, QPushButton, QVBoxLayout, QWidget)

from config.categories import NOTE_TYPE_COLORS
from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository

logger = logging.getLogger(__name__)

_SCALE = 400.0
_NODE_R = 10.0

# Ctrl+휠 확대/축소 설정.
_ZOOM_STEP = 1.15      # 한 노치당 배율
_ZOOM_MIN = 0.2        # 최소 누적 배율
_ZOOM_MAX = 5.0        # 최대 누적 배율


class ZoomableGraphicsView(QGraphicsView):
    """마우스 오버 상태에서 Ctrl+휠로 확대/축소되는 그래프 뷰.

    Ctrl 키 없이 휠을 돌리면 기본 스크롤 동작을 유지한다. 누적 배율은
    :data:`_ZOOM_MIN`~:data:`_ZOOM_MAX` 범위로 제한한다.
    """

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self._zoom = 1.0
        # 휠 위치를 기준으로 확대/축소되도록 앵커를 설정한다.
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def reset_zoom(self) -> None:
        """배율을 1.0 으로 되돌린다."""
        if self._zoom != 1.0:
            self.scale(1.0 / self._zoom, 1.0 / self._zoom)
            self._zoom = 1.0

    def zoom_by(self, factor: float) -> None:
        """현재 배율에 ``factor`` 를 곱하되, 허용 범위로 제한한다."""
        target = self._zoom * factor
        target = max(_ZOOM_MIN, min(_ZOOM_MAX, target))
        applied = target / self._zoom
        if applied != 1.0:
            self.scale(applied, applied)
            self._zoom = target

    @property
    def zoom(self) -> float:
        return self._zoom

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.modifiers() & Qt.ControlModifier:
            step = _ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP
            self.zoom_by(step)
            event.accept()
        else:
            super().wheelEvent(event)


class GraphPanel(QWidget):
    """노트-태그 관계를 보여주는 그래프 패널.

    노드 클릭 시 노트 이동은 MVP 이후 확장 지점으로 둔다.
    그래프 뷰에 마우스를 올린 뒤 Ctrl+휠 스크롤로 확대/축소할 수 있다.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._notes = NoteRepository()
        self._tags = TagRepository()

        layout = QVBoxLayout(self)
        refresh_btn = QPushButton("그래프 새로고침")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        self._scene = QGraphicsScene(self)
        self._view = ZoomableGraphicsView(self._scene, self)
        self._view.setRenderHints(self._view.renderHints())
        self._view.setToolTip("Ctrl + 마우스 휠로 확대/축소")
        layout.addWidget(self._view, 1)

        self.refresh()

    def _build_graph(self) -> nx.Graph:
        graph = nx.Graph()
        for note in self._notes.list_all():
            graph.add_node(note.id, label=note.title, kind="note",
                           note_type=note.note_type)
            for tag in self._tags.get_tags_for_note(note.id):
                tag_node = f"tag:{tag.name}"
                graph.add_node(tag_node, label=tag.name, kind="tag")
                graph.add_edge(note.id, tag_node)
        return graph

    def refresh(self) -> None:
        self._scene.clear()
        graph = self._build_graph()
        if graph.number_of_nodes() == 0:
            self._scene.addText("표시할 노트가 없습니다.")
            return

        positions = nx.spring_layout(graph, seed=42)

        # 엣지 먼저 그린다.
        edge_pen = QPen(QColor("#666666"))
        for source, target in graph.edges():
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            self._scene.addLine(x1 * _SCALE, y1 * _SCALE,
                                x2 * _SCALE, y2 * _SCALE, edge_pen)

        # 노드.
        for node, (x, y) in positions.items():
            data = graph.nodes[node]
            if data.get("kind") == "note":
                color = NOTE_TYPE_COLORS.get(data.get("note_type"), "#777777")
            else:
                color = "#CCCCCC"
            cx, cy = x * _SCALE, y * _SCALE
            ellipse = QGraphicsEllipseItem(cx - _NODE_R, cy - _NODE_R,
                                           _NODE_R * 2, _NODE_R * 2)
            ellipse.setBrush(QBrush(QColor(color)))
            ellipse.setPen(QPen(Qt.NoPen))
            self._scene.addItem(ellipse)

            label = self._scene.addText(data.get("label", ""))
            label.setDefaultTextColor(QColor("#dddddd"))
            label.setPos(cx + _NODE_R, cy - _NODE_R)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    widget = GraphPanel()
    widget.resize(900, 700)
    widget.show()
    sys.exit(app.exec())
