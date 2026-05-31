"""Export service: Markdown, JSON and GEXF tag-graph exports."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import networkx as nx

from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository

logger = logging.getLogger(__name__)


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class ExportService:
    """노트를 다양한 형식으로 내보낸다."""

    def __init__(self) -> None:
        self._notes = NoteRepository()
        self._tags = TagRepository()

    def export_note_markdown(self, note_id: str, output_path: str) -> None:
        note = self._notes.get_by_id(note_id)
        if note is None:
            raise ValueError(f"Note not found: {note_id}")

        tags = self._tags.get_tags_for_note(note_id)
        lines = [
            f"# {note.title}",
            "",
            f"- 유형: {note.note_type}",
            f"- 생성: {_iso(note.created_at)}",
            f"- 수정: {_iso(note.updated_at)}",
        ]
        if tags:
            lines.append("- 태그: " + ", ".join(f"#{t.name}" for t in tags))
        lines += ["", note.body or ""]

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    def export_all_json(self, output_path: str) -> None:
        payload = []
        for note in self._notes.list_all():
            tags = self._tags.get_tags_for_note(note.id)
            payload.append({
                "id": note.id,
                "title": note.title,
                "body": note.body,
                "note_type": note.note_type,
                "is_pinned": bool(note.is_pinned),
                "color_hint": note.color_hint,
                "created_at": _iso(note.created_at),
                "updated_at": _iso(note.updated_at),
                "tags": [t.name for t in tags],
            })

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def export_tag_graph_gexf(self, output_path: str) -> None:
        graph = nx.Graph()
        for note in self._notes.list_all():
            graph.add_node(note.id, label=note.title, kind="note",
                           note_type=note.note_type)
            for tag in self._tags.get_tags_for_note(note.id):
                tag_node = f"tag:{tag.name}"
                graph.add_node(tag_node, label=tag.name, kind="tag")
                graph.add_edge(note.id, tag_node)

        nx.write_gexf(graph, output_path)
