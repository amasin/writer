#!/usr/bin/env python3
"""
Google Search Console Performance Agent

Provides performance insights by querying the Google Search Console API.
In a production setup this agent would handle OAuth authentication, request
quota, and rate limiting. For this exercise we simulate the API and store
results in a local cache to avoid repeated calls.

The agent exposes methods for other components to fetch site-level metrics,
page-level metrics, top queries, and to detect opportunities such as pages
with low CTR or keywords ranking well but with low impressions.

All communication occurs over the A2A protocol; other agents send REQUEST
messages with `request_type` specifying the action (e.g. "get_site_performance").

Caching is implemented via a JSON file at `data/gsc_cache.json`.
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load .env file to ensure API credentials are available
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / '.env', override=True)
except ImportError:
    pass

from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType


class GSCPerformanceAgent(A2AAgent):
    """Agent that interacts with Google Search Console and returns performance data."""

    def __init__(self, agent_id: str = "gsc_performance_agent"):
        super().__init__(agent_id, AgentType.WORDPRESS_WRITER_AGENT)

                
        # Explicitly load .env to ensure variables are available
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent / '.env'
            load_dotenv(dotenv_path=env_path, override=True)
        except ImportError:
            pass
        
        self.cache_path = Path(__file__).parent / "data" / "gsc_cache.json"
        self._ensure_cache_dir()
        self.cache = self._load_cache()
        self.api_key = os.getenv("GSC_API_KEY")  # placeholder for real auth
        self.message_broker = None

    def set_message_broker(self, broker) -> None:
        """Attach the message broker for A2A communication."""
        self.message_broker = broker

    def _ensure_cache_dir(self):
        directory = self.cache_path.parent
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, Any]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[GSC] Failed to write cache: {e}")

    # ---- API utility methods (stubs / mocks) ----
    def authenticate_gsc(self) -> bool:
        """Perform authentication with Google Search Console.
        (Mocked) Returns True if an API key is present.
        """
        return bool(self.api_key)

    def fetch_site_performance(self) -> Dict[str, Any]:
        """Fetch aggregated site performance metrics.
        Caches results under key 'site'.
        """
        if "site" in self.cache:
            return self.cache["site"]
        data = {
            "clicks": random.randint(1000, 10000),
            "impressions": random.randint(10000, 100000),
            "ctr": round(random.uniform(0.01, 0.1), 4),
            "position": round(random.uniform(1, 10), 2),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        self.cache["site"] = data
        self._save_cache()
        return data

    def fetch_page_performance(self, url: str) -> Dict[str, Any]:
        """Return performance metrics for a given page URL."""
        key = f"page:{url}"
        if key in self.cache:
            return self.cache[key]
        data = {
            "url": url,
            "clicks": random.randint(10, 500),
            "impressions": random.randint(100, 5000),
            "ctr": round(random.uniform(0.005, 0.1), 4),
            "position": round(random.uniform(1, 100), 2),
        }
        self.cache[key] = data
        self._save_cache()
        return data

    def fetch_top_queries(self, url: str) -> List[str]:
        """Return list of top queries for the given page."""
        key = f"queries:{url}"
        if key in self.cache:
            return self.cache[key]
        queries = [f"{url.split('/')[-1]} keyword {i}" for i in range(1, 6)]
        self.cache[key] = queries
        self._save_cache()
        return queries

    def detect_low_ctr_pages(self) -> List[str]:
        """Return list of cached page URLs with CTR below threshold."""
        low = []
        for k, v in self.cache.items():
            if k.startswith("page:") and v.get("ctr", 1) < 0.02:
                low.append(v.get("url"))
        return low

    def detect_keyword_opportunities(self) -> List[str]:
        """Return keywords where position is high but impressions are low."""
        # this is mocked: return some static set
        return ["opportunity1", "opportunity2"]

    def analyze_site(self) -> Dict[str, Any]:
        """Convenience method that aggregates multiple insights."""
        site_data = self.fetch_site_performance()
        low_pages = self.detect_low_ctr_pages()
        keywords = self.detect_keyword_opportunities()
        return {
            "site_performance": site_data,
            "low_ctr_pages": low_pages,
            "keyword_opportunities": keywords
        }

    # ---- Message handling ----
    def process_message(self, message: A2AMessage) -> A2AMessage:
        if message.message_type != MessageType.REQUEST:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Invalid message type"}
            )

        req = message.payload.get("request_type")
        if req == "analyze_site":
            data = self.analyze_site()
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.RESPONSE,
                payload={"gsc_data": data}
            )
        elif req == "get_page_performance":
            url = message.payload.get("url", "")
            data = self.fetch_page_performance(url)
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.RESPONSE,
                payload={"page_performance": data}
            )
        else:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": f"Unknown request_type {req}"}
            )
