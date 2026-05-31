"""Tests for the rule-based note type classifier."""

from __future__ import annotations

import pytest

from services.classifier import NoteClassifier


@pytest.mark.parametrize("title, body, expected", [
    ("코드 정리", "def main(): pass 함수 정리", "LEARNING"),
    ("오늘 기분", "너무 우울하고 무기력하다", "MOOD"),
    ("새 아이디어", "이런 앱을 만들고 싶어", "IDEA"),
    ("자수 도안", "구매한 패턴 파일 보관", "ARCHIVE"),
])
def test_suggest_type_matches_keywords(db, title, body, expected):
    classifier = NoteClassifier()
    assert classifier.suggest_type(title, body) == expected


def test_suggest_type_defaults_to_idea(db):
    classifier = NoteClassifier()
    assert classifier.suggest_type("xyz", "별다른 키워드가 없는 내용") == "IDEA"


def test_suggest_type_empty_defaults_to_idea(db):
    classifier = NoteClassifier()
    assert classifier.suggest_type("", "") == "IDEA"


def test_learning_keyword_priority_over_later_types(db):
    # LEARNING 키워드가 먼저 매칭되어야 한다.
    classifier = NoteClassifier()
    assert classifier.suggest_type("학습", "공부하면서 우울했지만") == "LEARNING"
