"""
State management for LangGraph workflow.
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum
import operator

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from .logging import get_logger

logger = get_logger(__name__)


class MessageRole(str, Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Structured message model."""
    id: str = Field(default_factory=lambda: f"msg_{int(datetime.utcnow().timestamp() * 1000)}")
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class AgentType(str, Enum):
    """Agent types."""
    ORCHESTRATOR = "orchestrator"
    ACTION = "action"
    PROFILE = "profile"
    TAX_KNOWLEDGE = "tax_knowledge"
    PRESENTER = "presenter"


class AgentResponse(BaseModel):
    """Agent response model."""
    agent_type: AgentType
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: Optional[float] = None
    tokens_used: Optional[int] = None
    
    class Config:
        use_enum_values = True


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    annual_income: Optional[float] = None
    employment_status: Optional[str] = None
    filing_status: Optional[str] = None
    dependents: int = 0
    conversation_count: int = 0
    last_interaction: Optional[datetime] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationContext(BaseModel):
    """Conversation context model."""
    session_id: str
    user_id: str
    current_topic: Optional[str] = None
    conversation_stage: str = "initial"
    user_intent: Optional[str] = None
    requires_profile_update: bool = False
    requires_tax_analysis: bool = False
    requires_tax_guidance: bool = False
    requires_actions: bool = False
    profile_confirmed: bool = False
    last_profile_update: Optional[datetime] = None
    context_updates: Dict[str, Any] = Field(default_factory=dict)


class WorkflowState(TypedDict):
    """Main workflow state for LangGraph."""
    # Core conversation data
    user_message: str
    session_id: str
    user_id: str
    
    # Message history
    messages: Annotated[List[Message], operator.add]
    agent_responses: Annotated[List[AgentResponse], operator.add]
    
    # User profile and context
    user_profile: Optional[UserProfile]
    context: ConversationContext
    
    # Workflow control
    current_agent: Optional[AgentType]
    next_agent: Optional[AgentType]
    workflow_complete: bool
    
    # Error handling
    error_message: Optional[str]
    retry_count: int
    
    # Performance metrics
    start_time: datetime
    execution_metrics: Dict[str, Any]


class StateManager:
    """Manages workflow state operations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def create_initial_state(
        self, 
        user_message: str, 
        session_id: str, 
        user_id: str,
        user_profile: Optional[UserProfile] = None
    ) -> WorkflowState:
        """Create initial workflow state."""
        return WorkflowState(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            messages=[],
            agent_responses=[],
            user_profile=user_profile,
            context=ConversationContext(
                session_id=session_id,
                user_id=user_id,
                conversation_stage="initial"
            ),
            current_agent=None,
            next_agent=None,
            workflow_complete=False,
            error_message=None,
            retry_count=0,
            start_time=datetime.utcnow(),
            execution_metrics={}
        )
    
    def add_user_message(self, state: WorkflowState, content: str) -> WorkflowState:
        """Add user message to state."""
        message = Message(
            role=MessageRole.USER,
            content=content,
            metadata={"session_id": state["session_id"]}
        )
        state["messages"].append(message)
        return state
    
    def add_agent_response(self, state: WorkflowState, response: AgentResponse) -> WorkflowState:
        """Add agent response to state."""
        state["agent_responses"].append(response)
        
        # Add assistant message
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
            metadata={
                "agent_type": response.agent_type,
                "confidence": response.confidence,
                "reasoning": response.reasoning
            }
        )
        state["messages"].append(assistant_message)
        
        return state
    
    def update_context(self, state: WorkflowState, updates: Dict[str, Any]) -> WorkflowState:
        """Update conversation context."""
        context = state["context"]
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.context_updates[key] = value
        
        state["context"] = context
        return state
    
    def set_next_agent(self, state: WorkflowState, agent_type: AgentType) -> WorkflowState:
        """Set next agent to execute."""
        state["next_agent"] = agent_type
        return state
    
    def complete_workflow(self, state: WorkflowState) -> WorkflowState:
        """Mark workflow as complete."""
        state["workflow_complete"] = True
        state["execution_metrics"]["total_time"] = (
            datetime.utcnow() - state["start_time"]
        ).total_seconds()
        return state
    
    def handle_error(self, state: WorkflowState, error_message: str) -> WorkflowState:
        """Handle workflow error."""
        state["error_message"] = error_message
        state["retry_count"] += 1
        self.logger.error(f"Workflow error: {error_message}", extra={
            "session_id": state["session_id"],
            "retry_count": state["retry_count"]
        })
        return state
    
    def get_conversation_history(self, state: WorkflowState, limit: int = 10) -> List[Message]:
        """Get recent conversation history."""
        return state["messages"][-limit:] if state["messages"] else []
    
    def get_agent_responses(self, state: WorkflowState, agent_type: Optional[AgentType] = None) -> List[AgentResponse]:
        """Get agent responses, optionally filtered by agent type."""
        responses = state["agent_responses"]
        if agent_type:
            return [r for r in responses if r.agent_type == agent_type]
        return responses
    
    def should_retry(self, state: WorkflowState, max_retries: int = 3) -> bool:
        """Check if workflow should retry after error."""
        return state["retry_count"] < max_retries and not state["workflow_complete"]


# Global state manager
state_manager = StateManager()
