"""Agent responsible for planning article intent, angle, and structure style."""

from __future__ import annotations

import random
from typing import Dict, Any

from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType
from seo_brief import build_brief
from logging_setup import get_logger

logger = get_logger(__name__)


class PlannerAgent(A2AAgent):
    def __init__(self, agent_id: str = "planner_agent"):
        super().__init__(agent_id, AgentType.WORDPRESS_WRITER_AGENT)

    def process_message(self, message: A2AMessage) -> A2AMessage:
        if message.message_type != MessageType.REQUEST:
            return self._error(message, "Invalid message type")
        topic = message.payload.get("topic")
        if not topic:
            return self._error(message, "No topic provided")

        brief = build_brief(topic)
        # choose an angle based on queries or random
        if brief.secondary_keywords:
            brief.angle = f"Focus on {brief.secondary_keywords[0]}"
        else:
            brief.angle = random.choice(["Beginner's guide", "Advanced strategies", "Case studies"])

        # pick search intent heuristically
        brief.search_intent = random.choice(["informational", "commercial", "how-to"])
        # audience
        brief.audience = random.choice(["general", "developer", "business"])

        # style seed for outline variation
        style_seed = random.randint(0, 7)

        payload = {"brief": brief, "style_seed": style_seed}
        return A2AMessage(sender=self.agent_id, receiver=message.sender, message_type=MessageType.RESPONSE, payload=payload)

    def _error(self, message: A2AMessage, text: str):
        return A2AMessage(sender=self.agent_id, receiver=message.sender, message_type=MessageType.ERROR, payload={"error": text})
