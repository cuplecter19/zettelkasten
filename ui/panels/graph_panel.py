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


class GraphPanel(QWidget):
    """노트-태그 관계를 보여주는 그래프 패널.

    노드 클릭 시 노트 이동은 MVP 이후 확장 지점으로 둔다.
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
        self._view = QGraphicsView(self._scene, self)
        self._view.setRenderHints(self._view.renderHints())
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
