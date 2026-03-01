#!/usr/bin/env python3
"""
WordPress Content Index Module

Provides functionality to fetch posts from WordPress, build an index,
detect duplicate titles and outlines, and cache results locally.

Uses REST API with Application Password authentication.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin
import base64


class WPContentIndex:
    """Manages WordPress content indexing and duplicate detection."""

    def __init__(self):
        """Initialize with WordPress credentials from .env."""
        self.base_url = os.getenv("WP_BASE_URL", "https://aitopchoices.com")
        self.username = os.getenv("WP_USERNAME", "")
        self.app_password = os.getenv("WP_APP_PASSWORD", "")
        
        self.cache_path = Path(__file__).parent / "data" / "wp_index_cache.json"
        self.cache_ttl_hours = 6
        self.posts_index: List[Dict[str, Any]] = []
        self.index_built = False

    def _ensure_cache_dir(self):
        """Create cache directory if needed."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_auth_header(self) -> str:
        """Create Basic Auth header from username and app password."""
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _load_cache(self) -> Optional[Tuple[List[Dict], float]]:
        """Load index from cache if valid."""
        if not self.cache_path.exists():
            return None
        
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            timestamp = data.get("timestamp", 0)
            age_hours = (time.time() - timestamp) / 3600
            
            if age_hours < self.cache_ttl_hours:
                return data.get("posts", []), timestamp
        except Exception:
            pass
        
        return None

    def _save_cache(self, posts: List[Dict]):
        """Save index to cache with timestamp."""
        self._ensure_cache_dir()
        try:
            data = {
                "timestamp": time.time(),
                "posts": posts
            }
            self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WP Index] Failed to save cache: {e}")

    def fetch_posts(self, post_type: str = "posts", per_page: int = 100, 
                   max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch posts from WordPress REST API.
        
        Args:
            post_type: "posts", "pages", or custom post type
            per_page: Posts per page (max 100)
            max_pages: Maximum pages to fetch
            
        Returns:
            List of post dictionaries with title, slug, link, date, content
        """
        if not self.username or not self.app_password:
            print("[WP Index] No WordPress credentials available; using mock data")
            return self._mock_posts()
        
        all_posts = []
        auth = self._get_auth_header()
        
        for page in range(1, max_pages + 1):
            try:
                import urllib.request
                
                endpoint = urljoin(self.base_url, f"/wp-json/wp/v2/{post_type}")
                url = f"{endpoint}?per_page={per_page}&page={page}&orderby=date&order=desc"
                
                req = urllib.request.Request(url)
                req.add_header("Authorization", auth)
                req.add_header("User-Agent", "WriterAgent/1.0")
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    posts = json.loads(response.read().decode())
                    
                    if not posts:
                        break
                    
                    for post in posts:
                        all_posts.append({
                            "title": post.get("title", {}).get("rendered", ""),
                            "slug": post.get("slug", ""),
                            "link": post.get("link", ""),
                            "date": post.get("date", ""),
                            "content": post.get("content", {}).get("rendered", ""),
                            "id": post.get("id")
                        })
            
            except Exception as e:
                print(f"[WP Index] Error fetching page {page}: {e}")
                break
        
        return all_posts

    def _mock_posts(self) -> List[Dict[str, Any]]:
        """Return mock posts for testing."""
        return [
            {
                "title": "The Ultimate Guide to Artificial Intelligence",
                "slug": "ultimate-guide-ai",
                "link": "https://aitopchoices.com/ultimate-guide-ai",
                "date": "2026-03-01",
                "content": "<h2>What is AI</h2><h2>Benefits</h2><h2>Challenges</h2>",
                "id": 1
            },
            {
                "title": "AI Tools: Complete Overview",
                "slug": "ai-tools-overview",
                "link": "https://aitopchoices.com/ai-tools-overview",
                "date": "2026-02-28",
                "content": "<h2>AI Tools</h2><h2>Use Cases</h2>",
                "id": 2
            }
        ]

    def build_index(self, posts: List[Dict]) -> List[Dict]:
        """
        Build searchable index from posts.
        
        Args:
            posts: List of post dicts from fetch_posts()
            
        Returns:
            Indexed posts with normalized titles, headings, etc.
        """
        indexed = []
        
        for post in posts:
            indexed.append({
                "title": post.get("title", ""),
                "title_normalized": self.normalize_text(post.get("title", "")),
                "slug": post.get("slug", ""),
                "link": post.get("link", ""),
                "date": post.get("date", ""),
                "headings": self.extract_headings(post.get("content", "")),
                "content_length": len(post.get("content", ""))
            })
        
        self.posts_index = indexed
        self.index_built = True
        return indexed

    def load_or_build(self) -> List[Dict]:
        """Load from cache or fetch and build index."""
        cached = self._load_cache()
        if cached:
            posts, _ = cached
            print(f"[WP Index] Loaded {len(posts)} posts from cache")
            return self.build_index(posts)
        
        print("[WP Index] Building index from WordPress...")
        posts = self.fetch_posts()
        self._save_cache(posts)
        return self.build_index(posts)

    @staticmethod
    def normalize_text(s: str) -> str:
        """Normalize text for comparison."""
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    @staticmethod
    def title_similarity(a: str, b: str) -> float:
        """
        Calculate similarity between two titles using token Jaccard.
        Optionally uses Levenshtein if available.
        
        Returns:
            Similarity score 0.0-1.0
        """
        # Token-based Jaccard similarity
        normalize = WPContentIndex.normalize_text
        tokens_a = set(normalize(a).split())
        tokens_b = set(normalize(b).split())
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        jaccard = intersection / union if union > 0 else 0.0
        
        # Try Levenshtein for string-level similarity
        try:
            from rapidfuzz import fuzz
            lev_sim = fuzz.ratio(normalize(a), normalize(b)) / 100.0
            return (jaccard + lev_sim) / 2.0
        except ImportError:
            return jaccard

    def find_duplicate_title(self, candidate_title: str, threshold: float = 0.85
                            ) -> Dict[str, Any]:
        """
        Find if candidate title is duplicate of existing posts.
        
        Args:
            candidate_title: Title to check
            threshold: Similarity threshold above which is considered duplicate
            
        Returns:
            {"is_duplicate": bool, "matches": [{"title": ..., "similarity": ..., "link": ...}]}
        """
        if not self.index_built:
            self.load_or_build()
        
        matches = []
        
        for post in self.posts_index:
            similarity = self.title_similarity(candidate_title, post["title"])
            
            if similarity >= threshold:
                matches.append({
                    "title": post["title"],
                    "similarity": round(similarity, 3),
                    "link": post["link"]
                })
        
        return {
            "is_duplicate": len(matches) > 0,
            "matches": matches
        }

    @staticmethod
    def extract_headings(html: str) -> List[str]:
        """Extract H2 and H3 headings from HTML."""
        headings = []
        
        # Extract H2s
        for match in re.finditer(r'<h2[^>]*>([^<]+)</h2>', html, re.IGNORECASE):
            headings.append(match.group(1).strip())
        
        # Extract H3s
        for match in re.finditer(r'<h3[^>]*>([^<]+)</h3>', html, re.IGNORECASE):
            headings.append(match.group(1).strip())
        
        return headings

    @staticmethod
    def outline_similarity(outline_headings: List[str], 
                          existing_headings: List[str]) -> float:
        """
        Calculate similarity between two outlines.
        
        Args:
            outline_headings: Candidate outline headings
            existing_headings: Existing post headings
            
        Returns:
            Similarity 0.0-1.0
        """
        if not outline_headings or not existing_headings:
            return 0.0
        
        normalize = WPContentIndex.normalize_text
        candidate_set = set(normalize(h) for h in outline_headings)
        existing_set = set(normalize(h) for h in existing_headings)
        
        intersection = len(candidate_set & existing_set)
        candidate_count = len(candidate_set)
        
        return intersection / candidate_count if candidate_count > 0 else 0.0

    def find_duplicate_outline(self, outline_headings: List[str], threshold: float = 0.7
                              ) -> Dict[str, Any]:
        """
        Find if outline is duplicate of existing posts.
        
        Args:
            outline_headings: List of heading strings
            threshold: Similarity threshold
            
        Returns:
            {"is_duplicate": bool, "matches": [{"title": ..., "similarity": ..., "link": ...}]}
        """
        if not self.index_built:
            self.load_or_build()
        
        matches = []
        
        for post in self.posts_index:
            if not post["headings"]:
                continue
            
            similarity = self.outline_similarity(outline_headings, post["headings"])
            
            if similarity >= threshold:
                matches.append({
                    "title": post["title"],
                    "similarity": round(similarity, 3),
                    "link": post["link"],
                    "shared_sections": len(
                        set(self.normalize_text(h) for h in outline_headings) &
                        set(self.normalize_text(h) for h in post["headings"])
                    )
                })
        
        return {
            "is_duplicate": len(matches) > 0,
            "matches": matches
        }


def load_or_build() -> List[Dict]:
    """Convenience function to load/build WP index."""
    indexer = WPContentIndex()
    return indexer.load_or_build()
