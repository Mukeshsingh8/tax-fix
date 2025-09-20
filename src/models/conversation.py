"""Conversation and message models."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"


class MessageType(str, Enum):
    """Message type enumeration."""
    TEXT = "text"
    ACTION = "action"
    SUGGESTION = "suggestion"
    REASONING = "reasoning"
    ERROR = "error"


class AgentType(str, Enum):
    """Agent type enumeration."""
    ORCHESTRATOR = "orchestrator"
    PROFILE = "profile"
    TAX_KNOWLEDGE = "tax_knowledge"
    MEMORY = "memory"
    ACTION = "action"


class Message(BaseModel):
    """Individual message in a conversation."""
    id: str = Field(..., description="Unique message ID")
    conversation_id: str = Field(..., description="Associated conversation ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT)
    agent_type: Optional[AgentType] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentResponse(BaseModel):
    """Response from an agent."""
    agent_type: AgentType
    content: str
    reasoning: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(BaseModel):
    """Conversation model."""
    id: str = Field(..., description="Unique conversation ID")
    user_id: str = Field(..., description="Associated user ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Message] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: str = Field(default="active")  # active, completed, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent messages from the conversation."""
        return self.messages[-limit:] if self.messages else []
    
    def get_messages_by_agent(self, agent_type: AgentType) -> List[Message]:
        """Get messages from a specific agent."""
        return [msg for msg in self.messages if msg.agent_type == agent_type]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
