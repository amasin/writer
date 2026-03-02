import pytest

from similarity import normalize_text, title_similarity, outline_similarity


def test_normalize_text():
    assert normalize_text("Hello, WORLD!") == "hello world"


def test_title_similarity_identical():
    assert title_similarity("AI Guide", "AI Guide") == 1.0


def test_title_similarity_partial():
    s = title_similarity("Artificial Intelligence Guide", "AI Guide")
    assert s > 0.0


def test_outline_similarity():
    a = ["What is AI?", "How to use AI"]
    b = ["What is AI", "Applications"]
    assert outline_similarity(a, b) > 0.0
