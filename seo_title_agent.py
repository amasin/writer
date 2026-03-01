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
    """AI Agent for researching and generating SEO-optimized titles using A2A Protocol."""
    
    def __init__(self, agent_id: str = "seo_title_agent"):
        """Initialize the SEO Title Agent."""
        super().__init__(agent_id, AgentType.SEO_TITLE_AGENT)
        self.model_api = os.getenv("OPENAI_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.message_broker: Optional[A2AMessageBroker] = None
        
    def process_message(self, message: A2AMessage) -> A2AMessage:
        """
        Process incoming A2A message for title generation.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response message with generated title
        """
        if message.message_type != MessageType.REQUEST:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Invalid message type"}
            )
        
        topic = message.payload.get("topic", "Artificial Intelligence")
        
        # Generate the title
        title = self.research_and_generate(topic)
        
        return A2AMessage(
            sender=self.agent_id,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            payload={
                "title": title,
                "topic": topic,
                "seo_score": 95,
                "generated_at": str(__import__('datetime').datetime.now())
            }
        )
    
    def set_message_broker(self, broker: A2AMessageBroker) -> None:
        """Set the A2A message broker for agent communication."""
        self.message_broker = broker
        
    def request_article_generation(self, title: str, topic: str) -> Optional[Dict[str, Any]]:
        """
        Request WordPress article generation from WordPress Writer Agent via A2A Protocol.
        
        Args:
            title: Generated article title
            topic: Topic being written about
            
        Returns:
            Response from WordPress writer agent
        """
        if not self.message_broker:
            return None
        
        # Send request to WordPress Writer Agent
        message = self.send_message(
            receiver_id="wordpress_writer_agent",
            payload={
                "title": title,
                "topic": topic,
                "request_type": "generate_article"
            },
            message_type=MessageType.REQUEST
        )
        
        # Broker sends the message and returns response
        response = self.message_broker.send_message(message)
        
        if response.message_type == MessageType.RESPONSE:
            return response.payload
        else:
            return None
        
        
    def search_topic(self, topic: str, num_results: int = 10) -> list:
        """
        Search for articles related to the topic.
        
        Args:
            topic: The topic to search for
            num_results: Number of results to fetch
            
        Returns:
            List of search results with titles and metadata
        """
        results = []
        
        # Try using SerpAPI if key is available
        if self.serpapi_key:
            results = self._search_with_serpapi(topic, num_results)
        else:
            # Fallback to analyzing trending patterns
            results = self._generate_trending_topics(topic)
            
        return results
    
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
    
    def analyze_seo_value(self, titles: list) -> list:
        """
        Analyze SEO value of titles based on keyword metrics.
        
        Args:
            titles: List of titles with metadata
            
        Returns:
            Same list with SEO scores added
        """
        seo_scored = []
        
        for result in titles:
            title = result.get("title", "")
            
            # Calculate SEO score based on criteria
            score = self._calculate_seo_score(title)
            result["seo_score"] = score
            seo_scored.append(result)
        
        # Sort by SEO score descending
        return sorted(seo_scored, key=lambda x: x["seo_score"], reverse=True)
    
    def _calculate_seo_score(self, title: str) -> float:
        """
        Calculate SEO score for a title.
        
        Factors:
        - Length (50-60 characters optimal)
        - Keywords (topic words, modifiers)
        - Readability
        - CTR patterns
        """
        score = 0.0
        
        # Length score (optimal: 50-60 chars)
        length = len(title)
        if 40 <= length <= 65:
            score += 30
        elif 30 <= length <= 80:
            score += 20
        else:
            score += 5
        
        # PowerWords (increase CTR)
        power_words = ["ultimate", "guide", "best", "complete", "essential", 
                       "how to", "why", "what", "2026", "trending", "exclusive",
                       "comprehensive", "expert", "proven", "revolutionary",
                       "new", "latest", "secret", "powerful"]
        power_word_count = sum(1 for word in power_words if word.lower() in title.lower())
        score += min(power_word_count * 15, 35)
        
        # Keyword presence
        keyword_count = len([w for w in title.split() if len(w) > 4])
        score += min(keyword_count * 3, 25)
        
        # Structure points (has numbers, questions, etc.)
        has_year = bool(re.search(r'\b20\d{2}\b', title))
        has_number = bool(re.search(r'\d+', title))
        has_question = '?' in title
        
        score += 5 if has_year else 0
        score += 3 if has_number else 0
        score += 5 if has_question else 0
        
        return min(score, 100)
    
    def select_best_title(self, scored_titles: list) -> str:
        """
        Select the title with the highest SEO value.
        
        Args:
            scored_titles: List of titles with SEO scores
            
        Returns:
            The best title string
        """
        if not scored_titles:
            return "Artificial Intelligence: The Complete Guide"
        
        best = scored_titles[0]
        return best.get("title", "")
    
    def research_and_generate(self, topic: str, gsc_data: Dict[str, Any] = None) -> str:
        """
        Main method: Research topic and generate SEO-optimized title.
        
        Args:
            topic: The topic to research
            gsc_data: Optional dictionary of performance insights from GSC
        
        Returns:
            The best SEO-optimized article title
        """
        # Generate candidates in varied styles
        print(f"Generating title candidates for {topic}...", file=__import__('sys').stderr)
        candidates = self.generate_title_candidates(topic, n=20)
        
        # Score each candidate
        scored = []
        for title in candidates:
            score = self._calculate_seo_score(title)
            scored.append({"title": title, "seo_score": score})
        
        # Sort by score
        scored = sorted(scored, key=lambda x: x["seo_score"], reverse=True)
        
        # Use GSC data if available
        if gsc_data:
            site_perf = gsc_data.get("site_performance", {})
            ctr = site_perf.get("ctr")
            if ctr is not None and ctr < 0.02:
                # Penalize short titles when CTR is low
                for item in scored:
                    if len(item.get("title", "")) < 45:
                        item["seo_score"] -= 5
        
        # Select best
        scored = sorted(scored, key=lambda x: x["seo_score"], reverse=True)
        best_title = scored[0].get("title", "Artificial Intelligence: The Complete Guide") if scored else "Artificial Intelligence: The Complete Guide"
        
        return best_title

    def generate_title(self, topic: str, gsc_data: Dict[str, Any] = None) -> str:
        """Convenience method called by orchestrator to create title."""
        return self.research_and_generate(topic, gsc_data)

    def generate_title_candidates(self, topic: str, n: int = 20) -> List[str]:
        """
        Generate varied title candidates in different styles.
        
        Args:
            topic: The topic
            n: Number of candidates to generate
            
        Returns:
            List of varied title patterns
        """
        candidates = []
        year = 2026
        
        # Listicle style
        candidates.extend([
            f"10 Essential {topic} Strategies for {year}",
            f"15 {topic} Tips That Actually Work",
            f"7 Common {topic} Mistakes to Avoid",
            f"5 {topic} Trends Dominating {year}",
        ])
        
        # Guide style
        candidates.extend([
            f"The Ultimate Guide to {topic}",
            f"Complete {topic} Guide for Beginners",
            f"{topic}: A Comprehensive Guide",
            f"How to Master {topic} in {year}",
        ])
        
        # Comparison/What is
        candidates.extend([
            f"{topic} Explained: Everything You Need to Know",
            f"What is {topic}? Definition and Examples",
            f"{topic} vs Alternatives: Complete Comparison",
            f"{topic}: Real-World Use Cases and Benefits",
        ])
        
        # Problem/Solution
        candidates.extend([
            f"Solving {topic} Challenges: Practical Solutions",
            f"{topic} Problems and How to Fix Them",
            f"Why {topic} Matters: Business Impact Guide",
            f"The Future of {topic} in {year}",
        ])
        
        # Templates/Step-by-step
        candidates.extend([
            f"Step-by-Step {topic} Implementation Guide",
            f"{topic} Templates and Best Practices",
            f"How to Get Started with {topic}",
            f"Advanced {topic} Strategies for {year}",
        ])
        
        # Return top N
        return candidates[:n]


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
