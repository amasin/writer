"""Text similarity utilities for titles, outlines, and content."""

from __future__ import annotations

import re
from typing import List

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None  # optional


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_similarity(a: str, b: str) -> float:
    """Return a similarity score between 0 and 1 for two titles."""
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return 0.0
    set_a = set(na.split())
    set_b = set(nb.split())
    jacc = len(set_a & set_b) / len(set_a | set_b)
    if fuzz:
        lev = fuzz.token_sort_ratio(a, b) / 100.0
        return max(jacc, lev)
    return jacc


def outline_similarity(outline: List[str], existing: List[str]) -> float:
    """Jaccard similarity of normalized heading sets."""
    if not outline or not existing:
        return 0.0
    set_a = set(normalize_text(h) for h in outline)
    set_b = set(normalize_text(h) for h in existing)
    return len(set_a & set_b) / len(set_a) if set_a else 0.0
