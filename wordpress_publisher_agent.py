#!/usr/bin/env python3
"""
WordPress Publisher Agent

Receives HTML content from ProofreaderAgent and publishes it to a WordPress site via
REST API. Communicates over A2A protocol.
"""

import os
from pathlib import Path
import requests
from typing import Dict, Any
from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType

# load .env if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass


class WordPressPublisherAgent(A2AAgent):
    """Agent that creates posts on a WordPress site."""

    def __init__(self, agent_id: str = "wordpress_publisher_agent"):
        super().__init__(agent_id, AgentType.WORDPRESS_WRITER_AGENT)
        
        # Explicitly load .env to ensure variables are available
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent / '.env'
            load_dotenv(dotenv_path=env_path, override=True)
        except ImportError:
            pass
        
        # configuration for the WP site
        self.site_url = os.getenv("WP_SITE_URL") or "https://aitopchoices.example.com"
        self.username = os.getenv("WP_USER")
        self.password = os.getenv("WP_PASS")
        # application password or basic auth
        self.auth = (self.username, self.password) if self.username and self.password else None
        self.message_broker: Optional[A2AMessageBroker] = None

    def set_message_broker(self, broker: A2AMessageBroker) -> None:
        """Set the A2A message broker for agent communication."""
        self.message_broker = broker

    def process_message(self, message: A2AMessage) -> A2AMessage:
        if message.message_type != MessageType.REQUEST:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Invalid message type"}
            )

        request_type = message.payload.get("request_type", "publish_article")

        if request_type == "publish_article":
            title = message.payload.get("title", "")
            content = message.payload.get("content", "")
            status = message.payload.get("status", "draft")
            seo_score = message.payload.get("seo_score", None)

            try:
                post_url = self.publish_post(title, content, status)
                return A2AMessage(
                    sender=self.agent_id,
                    receiver=message.sender,
                    message_type=MessageType.RESPONSE,
                    payload={
                        "post_url": post_url,
                        "seo_score": seo_score,
                        "published": True
                    }
                )
            except Exception as e:
                return A2AMessage(
                    sender=self.agent_id,
                    receiver=message.sender,
                    message_type=MessageType.ERROR,
                    payload={"error": str(e)}
                )
        else:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": f"Unknown request_type {request_type}"}
            )

    def publish_post(self, title: str, content: str, status: str = "publish") -> str:
        """Publish a new post to WordPress using REST API.

        Args:
            title: Post title
            content: HTML content
            status: post status (publish, draft, etc.)

        Returns:
            URL of the created post
        """
        if not self.auth:
            raise RuntimeError("WordPress credentials not configured (WP_USER/WP_PASS)")

        endpoint = f"{self.site_url.rstrip('/')}/wp-json/wp/v2/posts"
        data = {
            "title": title,
            "content": content,
            "status": status
        }
        resp = requests.post(endpoint, auth=self.auth, json=data, timeout=30)
        resp.raise_for_status()
        post = resp.json()
        return post.get("link", "")
