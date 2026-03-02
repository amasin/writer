"""WordPress REST API client built on top of http_client.HTTPClient."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from config import cfg
from http_client import HTTPClient
from logging_setup import get_logger

logger = get_logger(__name__)


class WPClient:
    def __init__(self):
        self.base = cfg.wp_base_url.rstrip('/')
        self.auth_header = self._build_auth()
        self.http = HTTPClient()

    def _build_auth(self) -> str:
        creds = f"{cfg.wp_username}:{cfg.wp_app_password}"
        token = base64.b64encode(creds.encode()).decode()
        return f"Basic {token}"

    def _endpoint(self, path: str) -> str:
        return f"{self.base}/wp-json/wp/v2/{path.lstrip('/')}"

    def fetch_posts(self, post_type: str = "posts", per_page: int = 100, max_pages: int = 10) -> List[Dict[str, Any]]:
        all_posts: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            url = self._endpoint(post_type)
            params = {"per_page": per_page, "page": page, "orderby": "date", "order": "desc"}
            try:
                resp = self.http.get(url, params=params, headers={"Authorization": self.auth_header})
                posts = resp.json()
                if not posts:
                    break
                all_posts.extend(posts)
            except Exception as e:
                logger.error(f"Error fetching posts page {page}: {e}")
                break
        return all_posts

    def create_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._endpoint(cfg.wp_post_type)
        headers = {"Authorization": self.auth_header, "Content-Type": "application/json"}
        resp = self.http.post(url, json=data, headers=headers)
        return resp.json()

    def update_post(self, post_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._endpoint(f"{cfg.wp_post_type}/{post_id}")
        headers = {"Authorization": self.auth_header, "Content-Type": "application/json"}
        resp = self.http.put(url, json=data, headers=headers)
        return resp.json()

    def get_post_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        url = self._endpoint(cfg.wp_post_type)
        params = {"slug": slug}
        resp = self.http.get(url, params=params, headers={"Authorization": self.auth_header})
        posts = resp.json()
        return posts[0] if posts else None
