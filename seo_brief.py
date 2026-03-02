"""Builds an SEO brief for a given topic using GSC and WP index data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from gsc_client import get_client as get_gsc_client
from wp_index import load_or_build
from similarity import normalize_text, title_similarity, outline_similarity
from logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class SEOBrief:
    topic: str
    primary_keyword: str
    secondary_keywords: List[str] = field(default_factory=list)
    search_intent: str = "informational"
    audience: str = "general"
    angle: str = ""
    suggested_title_patterns: List[str] = field(default_factory=list)
    suggested_outline_sections: List[str] = field(default_factory=list)
    faq_questions: List[str] = field(default_factory=list)
    internal_link_targets: List[Dict[str, Any]] = field(default_factory=list)
    gsc_insights: Dict[str, Any] = field(default_factory=dict)
    dedupe_warnings: Dict[str, Any] = field(default_factory=dict)


def build_brief(topic: str) -> SEOBrief:
    logger.info(f"Building SEO brief for topic: {topic}")
    gsc = get_gsc_client()
    wp_idx = load_or_build()

    # normalize topic
    primary = topic.lower()

    # gather GSC queries containing the topic
    queries = gsc.get_queries_for_topic_seed([topic])
    secondary = [q['keys'][0] for q in sorted(queries, key=lambda r: r.get('impressions',0), reverse=True)][:5]

    # identify internal link targets that share words
    related = []
    for post in wp_idx.index:
        if title_similarity(post['title'], topic) > 0.2 and post['link']:
            related.append({'title': post['title'], 'link': post['link']})

    # build FAQ questions from high-impression queries
    faq = [q['keys'][0] for q in queries if '?' in q['keys'][0]][:5]

    # assemble brief
    brief = SEOBrief(
        topic=topic,
        primary_keyword=primary,
        secondary_keywords=secondary,
        suggested_title_patterns=[
            f"The Ultimate Guide to {topic}",
            f"{topic} Explained: What You Need to Know",
            f"How to {topic} Like a Pro"
        ],
        suggested_outline_sections=[
            f"What is {topic}?",
            f"Why {topic} Matters",
            f"How to {topic}",
            f"Common Mistakes",
            "Conclusion and Next Steps"
        ],
        faq_questions=faq,
        internal_link_targets=related,
        gsc_insights={'queries': queries}
    )

    # dedupe warnings
    dup_titles = []
    for post in wp_idx.index:
        if title_similarity(post['title'], topic) >= 0.85:
            dup_titles.append({'title': post['title'], 'link': post['link']})
    if dup_titles:
        brief.dedupe_warnings['similar_existing_posts'] = dup_titles

    return brief
