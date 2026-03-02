"""Builds an in-memory index of live WordPress content.

No persistent title history is stored; everything is queried from the site and
cached briefly.  Provides methods for similarity checks used by the pipeline.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import cfg
from http_client import HTTPClient
from logging_setup import get_logger

logger = get_logger(__name__)


class WPIndex:
    def __init__(self):
        self.client = HTTPClient()
        self.wp = None  # will be assigned when needed
        self.index: List[Dict[str, Any]] = []
        self._cache_path = cfg.cache_dir / "wp_index.json"
        self._ttl = cfg.cache_ttl_seconds
        self._built = False

    def _ensure_client(self):
        if self.wp is None:
            # lazy import to avoid circularity
            from wp_client import WPClient
            self.wp = WPClient()

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        if not self._cache_path.exists():
            return None
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            ts = data.get("timestamp", 0)
            if time.time() - ts < self._ttl:
                logger.debug("Loaded WP index from cache")
                return data.get("posts", [])
        except Exception as e:
            logger.warning(f"Failed to read WP index cache: {e}")
        return None

    def _save_cache(self, posts: List[Dict[str, Any]]) -> None:
        try:
            cfg.cache_dir.mkdir(parents=True, exist_ok=True)
            data = {"timestamp": time.time(), "posts": posts}
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.debug("Saved WP index to cache")
        except Exception as e:
            logger.warning(f"Failed to write WP index cache: {e}")

    def build(self) -> List[Dict[str, Any]]:
        if self._built:
            return self.index

        self._ensure_client()
        posts = self._load_cache()
        if posts is None:
            logger.info("Fetching posts from WordPress for index build...")
            posts = self.wp.fetch_posts(post_type=cfg.wp_post_type)
            self._save_cache(posts)
        else:
            logger.info("Using cached posts for index")
        self.index = [self._normalize_post(p) for p in posts]
        self._built = True
        return self.index

    def _normalize_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": post.get("id"),
            "title": post.get("title", {}).get("rendered", ""),
            "slug": post.get("slug", ""),
            "link": post.get("link", ""),
            "date": post.get("date", ""),
            "headings": self.extract_headings(post.get("content", {}).get("rendered", "")),
            "content_snippet": post.get("content", {}).get("rendered", "")[:2000]
        }

    @staticmethod
    def extract_headings(html: str) -> List[str]:
        headings = []
        for level in (2, 3):
            pattern = rf"<h{level}[^>]*>([^<]+)</h{level}>"
            headings += re.findall(pattern, html)
        return headings

    # similarity helpers are implemented elsewhere (similarity.py)


# convenience function
_index_instance: Optional[WPIndex] = None

def load_or_build() -> WPIndex:
    global _index_instance
    if _index_instance is None:
        _index_instance = WPIndex()
        _index_instance.build()
    return _index_instance
