"""Agent that identifies existing posts which should be refreshed based on GSC data."""
from __future__ import annotations

from typing import Dict, Any, List

from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType
from gsc_client import get_client as get_gsc_client
from wp_index import load_or_build
from logging_setup import get_logger

logger = get_logger(__name__)


class RefreshAgent(A2AAgent):
    def __init__(self, agent_id: str = "refresh_agent"):
        super().__init__(agent_id, AgentType.WORDPRESS_WRITER_AGENT)

    def process_message(self, message: A2AMessage) -> A2AMessage:
        if message.message_type != MessageType.REQUEST:
            return self._error(message, "Invalid message type")
        days = message.payload.get("days", 28)
        min_impressions = message.payload.get("min_impressions", 200)
        position_range = message.payload.get("position_range", (5, 20))

        gsc = get_gsc_client()
        opportunities = gsc.get_low_ctr_opportunities(min_impressions=min_impressions,
                                                      position_range=position_range,
                                                      days=days)
        # map pages to posts
        wp_idx = load_or_build()
        hits: List[Dict[str, Any]] = []
        for row in opportunities:
            page = row['keys'][0]
            for post in wp_idx.index:
                if post['link'] and page in post['link']:
                    hits.append({"post": post, "gsc": row})
        payload = {"opportunities": hits}
        return A2AMessage(sender=self.agent_id, receiver=message.sender, message_type=MessageType.RESPONSE, payload=payload)

    def _error(self, message: A2AMessage, text: str):
        return A2AMessage(sender=self.agent_id, receiver=message.sender, message_type=MessageType.ERROR, payload={"error": text})
