"""Offline, rule-based + TF-IDF note classification.

No external/AI APIs are used. Type suggestion is purely rule based; tag
suggestion and clustering use scikit-learn locally.
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from sqlalchemy import text

from config.categories import KEYWORD_RULES
from config.settings import CLUSTER_MIN_NOTES
from db.database import get_session
from db.repositories.note_repo import NoteRepository
from db.repositories.tag_repo import TagRepository

logger = logging.getLogger(__name__)


class NoteClassifier:
    """규칙 기반 유형 제안과 TF-IDF 기반 태그 제안/군집화."""

    def __init__(self) -> None:
        self._notes = NoteRepository()
        self._tags = TagRepository()

    def suggest_type(self, title: str, body: str) -> str:
        """KEYWORD_RULES 순서대로 매칭. 없으면 'IDEA' 반환."""
        haystack = f"{title or ''}\n{body or ''}".lower()
        for note_type, keywords in KEYWORD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in haystack:
                    return note_type
        return "IDEA"

    def suggest_tags(self, note_id: str, body: str) -> list[str]:
        """TF-IDF로 유사 노트 태그 제안. 노트 수 < 50이면 [] 반환."""
        all_notes = self._notes.list_all()
        if len(all_notes) < CLUSTER_MIN_NOTES:
            return []

        # 지연 임포트로 sklearn 미설치 환경에서의 부작용을 줄인다.
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [f"{n.title}\n{n.body}" for n in all_notes]
        ids = [n.id for n in all_notes]
        try:
            target_index = ids.index(note_id)
        except ValueError:
            corpus.append(body or "")
            ids.append(note_id)
            target_index = len(ids) - 1

        try:
            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            # 어휘가 비어있는 경우(공백 본문 등).
            return []

        sims = cosine_similarity(matrix[target_index], matrix).ravel()
        # 자기 자신 제외 후 유사도 상위 노트 선택.
        ranked = sorted(
            ((score, idx) for idx, score in enumerate(sims)
             if idx != target_index and score > 0.0),
            reverse=True,
        )[:5]

        tag_counter: Counter[str] = Counter()
        for _score, idx in ranked:
            for tag in self._tags.get_tags_for_note(ids[idx]):
                tag_counter[tag.name] += 1

        return [name for name, _count in tag_counter.most_common(5)]

    def run_clustering(self) -> dict[int, list[str]]:
        """K-Means 군집화 후 classification_cache에 저장. QThread에서 호출."""
        all_notes = self._notes.list_all()
        if len(all_notes) < CLUSTER_MIN_NOTES:
            logger.info("Skipping clustering: only %d notes", len(all_notes))
            return {}

        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer

        corpus = [f"{n.title}\n{n.body}" for n in all_notes]
        ids = [n.id for n in all_notes]

        try:
            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return {}

        n_clusters = max(2, min(10, len(all_notes) // 10))
        model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = model.fit_predict(matrix)

        clusters: dict[int, list[str]] = {}
        for note_id, label in zip(ids, labels):
            clusters.setdefault(int(label), []).append(note_id)

        with get_session() as session:
            for note_id, label in zip(ids, labels):
                session.execute(
                    text(
                        "INSERT INTO classification_cache "
                        "(note_id, suggested_tags, cluster_id, updated_at) "
                        "VALUES (:note_id, :tags, :cluster, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(note_id) DO UPDATE SET "
                        "cluster_id=excluded.cluster_id, "
                        "updated_at=CURRENT_TIMESTAMP"
                    ),
                    {"note_id": note_id, "tags": json.dumps([]),
                     "cluster": int(label)},
                )

        logger.info("Clustering complete: %d clusters", n_clusters)
        return clusters
