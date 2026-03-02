#!/usr/bin/env python3
"""
AI Agent for researching topics and generating SEO-optimized article titles.
This agent researches the given topic on the internet and suggests the best
article title based on maximum SEO value.

Uses A2A Protocol to communicate with WordPress Writer Agent to create articles.
"""

import os
import json
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from urllib.parse import quote
from collections import Counter
from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType, A2AMessageBroker

# load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / '.env', override=True)
except ImportError:
    pass


class SEOTitleAgent(A2AAgent):
    """AI Agent for researching and generating SEO‑optimized titles."""

    def __init__(self, agent_id: str = "seo_title_agent"):
        super().__init__(agent_id, AgentType.SEO_TITLE_AGENT)
        self.model_api = os.getenv("OPENAI_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.message_broker: Optional[A2AMessageBroker] = None

    def set_message_broker(self, broker: A2AMessageBroker) -> None:
        self.message_broker = broker

    def process_message(self, message: A2AMessage) -> A2AMessage:
        if message.message_type != MessageType.REQUEST:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Invalid message type"}
            )

        brief = message.payload.get("brief")
        if brief is None:
            topic = message.payload.get("topic", "Artificial Intelligence")
            from seo_brief import build_brief
            brief = build_brief(topic)

        title = self.research_and_generate(brief)

        return A2AMessage(
            sender=self.agent_id,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            payload={
                "title": title,
                "brief": brief,
                "generated_at": str(__import__('datetime').datetime.now())
            }
        )

    def research_and_generate(self, brief: Any, n_candidates: int = 30) -> str:
        candidates = self.generate_title_candidates(brief, n=n_candidates)
        from wp_index import load_or_build
        wp_idx = load_or_build()
        scored: List[Dict[str, Any]] = []
        for t in candidates:
            dup = any(title_similarity(t, post["title"]) >= 0.85 for post in wp_idx.index)
            if dup:
                continue
            score = self._calculate_seo_score(t, brief)
            scored.append({"title": t, "seo_score": score})
        if not scored:
            return f"Comprehensive Guide to {brief.topic}"
        scored.sort(key=lambda x: x["seo_score"], reverse=True)
        return scored[0]["title"]

    def generate_title_candidates(self, brief: Any, n: int = 20) -> List[str]:
        topic = brief.topic
        angle = brief.angle or ""
        patterns = brief.suggested_title_patterns.copy()
        patterns.extend([
            f"{topic} {angle}" if angle else f"{topic} Explained",
            f"{topic}: {angle} Strategies" if angle else f"{topic} Strategies for Success",
            f"{topic} – What You Need to Know in 2026",
            f"{topic} for {brief.audience.capitalize()}s",
        ])
        patterns.extend([
            f"{len(patterns)} Key {topic} Insights",
            f"Everything About {topic} in Simple Terms",
            f"Should You Use {topic}? A Complete Guide",
        ])
        seen = set()
        out: List[str] = []
        for t in patterns:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
            if len(out) >= n:
                break
        return out

    def _calculate_seo_score(self, title: str, brief: Any) -> float:
        score = 0.0
        l = len(title)
        if 50 <= l <= 65:
            score += 5
        elif 40 <= l <= 75:
            score += 3
        if brief.primary_keyword.lower() in title.lower():
            score += 5
        for kw in brief.secondary_keywords:
            if kw.lower() in title.lower():
                score += 2
        power = ["ultimate", "guide", "best", "how to", "why", "what", "essential", "proven"]
        if any(p in title.lower() for p in power) or (brief.angle and brief.angle.lower() in title.lower()):
            score += 5
        for row in brief.gsc_insights.get('queries', []):
            q = row.get('keys', [None])[0]
            if q and q.lower() in title.lower():
                score += 2
        return score

    # retain legacy search helpers for optional use
    def search_topic(self, topic: str, num_results: int = 10) -> list:
        results = []
        if self.serpapi_key:
            results = self._search_with_serpapi(topic, num_results)
        else:
            results = self._generate_trending_topics(topic)
        return results

    # (remaining methods unchanged: _search_with_serpapi, _generate_trending_topics, analyze_seo_value, select_best_title)
    
    def _search_with_serpapi(self, topic: str, num_results: int) -> list:
        """Search using SerpAPI."""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": topic,
                "api_key": self.serpapi_key,
                "num": num_results,
                "engine": "google"
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("organic_results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "position": item.get("position", 0)
                })
            return results
        except Exception as e:
            print(f"Error with SerpAPI search: {e}")
            return self._generate_trending_topics(topic)
    
    def _generate_trending_topics(self, topic: str) -> list:
        """Generate trending article titles based on SEO best practices."""
        # High-traffic keywords and patterns for the topic
        trending_patterns = {
            "Artificial Intelligence": [
                "The Ultimate Guide to Artificial Intelligence in 2026",
                "How AI is Transforming Industries: A Complete Analysis",
                "Artificial Intelligence Trends 2026: What You Need to Know",
                "AI in Business: The Future of Digital Transformation",
                "Machine Learning vs AI: Key Differences Explained",
                "Artificial Intelligence Career Guide: Jobs and Opportunities",
                "AI Safety and Ethics: Critical Considerations",
                "Generative AI: From ChatGPT to Enterprise Solutions",
                "How to Learn Artificial Intelligence: Step-by-Step Guide",
                "Artificial Intelligence Examples: Real-World Applications",
            ]
        }
        
        titles = trending_patterns.get(topic, [f"{topic}: Complete Guide 2026"])
        
        return [{"title": t, "estimated_volume": 5000 + i*100, "score": 95-i*2} 
                for i, t in enumerate(titles)]


def main():
    """Main entry point with A2A Protocol integration."""
    # Import WordPress agent
    from wordpress_agent import WordPressArticleAgent
    
    # Initialize agents
    seo_agent = SEOTitleAgent(agent_id="seo_title_agent")
    wordpress_agent = WordPressArticleAgent(agent_id="wordpress_writer_agent")
    
    # Initialize message broker
    broker = A2AMessageBroker()
    broker.register_agent(seo_agent)
    broker.register_agent(wordpress_agent)
    
    # Set broker for SEO agent
    seo_agent.set_message_broker(broker)
    
    topic = "Artificial Intelligence"
    
    # Generate SEO-optimized title (no GSC context when run standalone)
    best_title = seo_agent.research_and_generate(topic)
    
    # Output only the title (as per user requirement)
    print(best_title)
    
    # Request article generation via A2A Protocol (silent operation)
    article_response = seo_agent.request_article_generation(best_title, topic)


if __name__ == "__main__":
    main()
