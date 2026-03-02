"""Simple HTTP client with retries and backoff."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from logging_setup import get_logger

logger = get_logger(__name__)


class HTTPClient:
    def __init__(self, timeout: float = 10.0, max_retries: int = 3, backoff_factor: float = 0.5):
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.timeout = timeout

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        try:
            logger.debug(f"HTTP {method} {url} kwargs={{{kwargs}}}")
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.error(f"HTTP request failed: {exc}")
            raise

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, params=params, **kwargs)

    def post(self, url: str, data: Any = None, json: Any = None, **kwargs: Any) -> requests.Response:
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url: str, data: Any = None, json: Any = None, **kwargs: Any) -> requests.Response:
        return self.request("PUT", url, data=data, json=json, **kwargs)
