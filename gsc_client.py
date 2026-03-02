"""Google Search Console helper.

Uses service account credentials to query performance data and caches results.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import cfg
from logging_setup import get_logger

logger = get_logger(__name__)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    service_account = None
    build = None


class GSCClient:
    def __init__(self):
        if not service_account or not build:
            raise ImportError("google-api-python-client not installed")
        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        creds = service_account.Credentials.from_service_account_file(
            cfg.google_application_credentials, scopes=scopes
        )
        self.service = build('searchconsole', 'v1', credentials=creds)
        self.cache_path = cfg.cache_dir / 'gsc_cache.json'
        self.ttl = cfg.cache_ttl_seconds

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        if not self.cache_path.exists():
            return None
        try:
            data = json.loads(self.cache_path.read_text(encoding='utf-8'))
            if time.time() - data.get('timestamp', 0) < self.ttl:
                logger.debug('Loaded GSC data from cache')
                return data.get('payload')
        except Exception as e:
            logger.warning(f"Failed to read GSC cache: {e}")
        return None

    def _save_cache(self, payload: Dict[str, Any]) -> None:
        try:
            cfg.cache_dir.mkdir(parents=True, exist_ok=True)
            data = {'timestamp': time.time(), 'payload': payload}
            self.cache_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to write GSC cache: {e}")

    def query_performance(self, start_date: str, end_date: str, dimensions: List[str],
                          filters: Optional[List[Dict[str, Any]]] = None,
                          row_limit: int = 5000) -> List[Dict[str, Any]]:
        """Utility wrapper for performance.query"""
        body: Dict[str, Any] = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit
        }
        if filters:
            body['dimensionFilterGroups'] = [{'filters': filters}]
        resp = self.service.searchanalytics().query(siteUrl=cfg.gsc_site_url, body=body).execute()
        return resp.get('rows', [])

    # high-level helpers
    def get_queries_for_topic_seed(self, seeds: List[str], days: int = 90) -> List[Dict[str, Any]]:
        # fetch queries and filter by seed terms
        rows = self.query_performance(self._date_days_ago(days), self._date_days_ago(1), ['query'])
        return [r for r in rows if any(seed.lower() in r['keys'][0].lower() for seed in seeds)]

    def get_low_ctr_opportunities(self, min_impressions: int = 100, position_range: tuple = (1, 20), days: int = 90) -> List[Dict[str, Any]]:
        rows = self.query_performance(self._date_days_ago(days), self._date_days_ago(1), ['page'], [])
        return [r for r in rows if r.get('impressions',0) >= min_impressions and position_range[0] <= r.get('position',0) <= position_range[1] and r.get('ctr',1) < 0.02]

    def get_query_gaps_for_page(self, page_url: str, days: int = 90) -> List[Dict[str, Any]]:
        filters = [{'dimension': 'page', 'operator': 'equals', 'expression': page_url}]
        return self.query_performance(self._date_days_ago(days), self._date_days_ago(1), ['query','page'], filters)

    def _date_days_ago(self, days: int) -> str:
        from datetime import datetime, timedelta
        return (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')


# singleton
_gsc_client: Optional[GSCClient] = None

def get_client() -> GSCClient:
    global _gsc_client
    if _gsc_client is None:
        _gsc_client = GSCClient()
    return _gsc_client
