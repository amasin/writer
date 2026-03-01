#!/usr/bin/env python3
"""
A2A Protocol for Agent-to-Agent Communication.
Enables communication between different AI agents in the WriterAgent system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import json


class AgentType(Enum):
    """Types of agents in the system."""
    SEO_TITLE_AGENT = "seo_title_agent"
    WORDPRESS_WRITER_AGENT = "wordpress_writer_agent"


class MessageType(Enum):
    """Types of messages that can be passed between agents."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class A2AMessage:
    """Message object for Agent-to-Agent communication."""
    sender: str
    receiver: str
    message_type: MessageType
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "metadata": self.metadata or {}
        }
    
    def to_json(self) -> str:
        """Convert message to JSON."""
        return json.dumps(self.to_dict())


class A2AAgent(ABC):
    """Base class for agents that support A2A protocol."""
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        """
        Initialize the A2A Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.message_queue: List[A2AMessage] = []
        self.response_cache: Dict[str, Any] = {}
    
    @abstractmethod
    def process_message(self, message: A2AMessage) -> A2AMessage:
        """
        Process incoming A2A message.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response message
        """
        pass
    
    def send_message(self, receiver_id: str, payload: Dict[str, Any],
                     message_type: MessageType = MessageType.REQUEST) -> A2AMessage:
        """
        Send a message to another agent.
        
        Args:
            receiver_id: ID of receiving agent
            payload: Message payload
            message_type: Type of message
            
        Returns:
            The sent message
        """
        message = A2AMessage(
            sender=self.agent_id,
            receiver=receiver_id,
            message_type=message_type,
            payload=payload
        )
        self.message_queue.append(message)
        return message
    
    def receive_message(self, message: A2AMessage) -> A2AMessage:
        """
        Receive and process a message from another agent.
        
        Args:
            message: The incoming message
            
        Returns:
            Response from processing the message
        """
        response = self.process_message(message)
        self.response_cache[message.sender] = response.payload
        return response
    
    def get_cached_response(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get cached response from another agent."""
        return self.response_cache.get(agent_id)


class A2AMessageBroker:
    """Message broker for managing communication between agents."""
    
    def __init__(self):
        """Initialize the message broker."""
        self.agents: Dict[str, A2AAgent] = {}
    
    def register_agent(self, agent: A2AAgent) -> None:
        """Register an agent with the broker."""
        self.agents[agent.agent_id] = agent
    
    def send_message(self, message: A2AMessage) -> A2AMessage:
        """
        Send a message through the broker.
        
        Args:
            message: The message to send
            
        Returns:
            Response from the receiving agent
        """
        receiver = self.agents.get(message.receiver)
        
        if not receiver:
            error_response = A2AMessage(
                sender="A2AMessageBroker",
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": f"Receiver {message.receiver} not found"}
            )
            return error_response
        
        response = receiver.receive_message(message)
        return response
    
    def get_agent(self, agent_id: str) -> Optional[A2AAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
