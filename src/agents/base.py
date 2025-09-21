"""Base agent class for all agents."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from ..core.state import Message, AgentResponse, AgentType
from ..services.llm import LLMService
from ..services.memory import MemoryService
from ..services.database import DatabaseService
from ..core.logging import get_logger


class BaseAgent(ABC):
    """
    Minimal shared backbone for all agents.

    Responsibilities:
    - Hold shared services (LLM, memory/cache, DB).
    - Provide a single way to create AgentResponse objects.
    - Optionally inject recent conversation history into LLM calls.
    - Centralize lightweight validation + logging helpers.

    Policy (kept generic here; concrete agents add specifics):
    - Always respond in English. German tax terms allowed with brief English context.
    """

    def __init__(
        self,
        agent_type: AgentType,
        llm_service: LLMService,
        memory_service: MemoryService,
        database_service: DatabaseService,
    ):
        self.agent_type = agent_type
        self.llm_service = llm_service
        self.memory_service = memory_service
        self.database_service = database_service
        # Clear, namespaced logger per agent
        name = getattr(agent_type, "value", str(agent_type))
        self.logger = get_logger(f"agent.{name}")

    # Core contract 

    @abstractmethod
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process a message and return the final response."""
        raise NotImplementedError

    async def get_system_prompt(self) -> str:
        """Default system prompt (agents typically override)."""
        name = getattr(self.agent_type, "value", str(self.agent_type))
        return (
            f"You are the {name} agent in a German tax assistant. "
            f"Answer in English. Use German tax terms with brief English explanations."
        )

    # Small utilities 

    async def validate_input(self, message: Message) -> bool:
        """Quick sanity check on inbound message."""
        return bool(message and isinstance(message.content, str) and message.content.strip())

    async def create_response(
        self,
        content: str,
        reasoning: Optional[str] = None,
        confidence: float = 0.8,
        suggested_actions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Create a standardized response envelope."""
        return AgentResponse(
            agent_type=self.agent_type,
            content=content,
            reasoning=reasoning,
            confidence=confidence,
            suggested_actions=suggested_actions or [],
            metadata=metadata or {},
        )

    async def log_interaction(self, message: Message, response: AgentResponse, session_id: str) -> None:
        """Uniform interaction log line."""
        try:
            mid = getattr(message, "id", "unknown")
            self.logger.info(
                f"{getattr(self.agent_type, 'value', self.agent_type)} handled message {mid} "
                f"(session {session_id}) with confidence {response.confidence:.2f}"
            )
        except Exception:
            # Never let logging break the flow
            pass

    # Conversation history & LLM glue 

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Fetch recent conversation messages for LLM context.
        1) Try cache (fast), 2) fall back to DB (reliable).
        Returns a list[{"role": "...", "content": "..."}].
        """
        try:
            # 1) Cache
            cached = await self.memory_service.get_cached_conversation_history(conversation_id, limit)
            if cached:
                self.logger.info(
                    f"History hit (cache): {len(cached)} messages for conversation {conversation_id}"
                )
                return [
                    {
                        "role": (getattr(msg.role, "value", msg.role) if hasattr(msg, "role") else "user"),
                        "content": getattr(msg, "content", ""),
                    }
                    for msg in cached
                ]

            # 2) DB fallback
            self.logger.info(f"History miss (cache) → DB fetch for conversation {conversation_id}")
            rows = await self.database_service.get_conversation_messages(conversation_id, limit=limit)
            # Cache for future requests
            if rows:
                await self.memory_service.cache_conversation_history(conversation_id, rows)

            return [
                {
                    "role": (getattr(msg.role, "value", msg.role) if hasattr(msg, "role") else "user"),
                    "content": getattr(msg, "content", ""),
                }
                for msg in rows
            ]
        except Exception as e:
            self.logger.error(f"History retrieval failed: {e}")
            return []

    async def generate_llm_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "groq",
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        include_history: bool = True,
    ) -> str:
        """
        Call the LLM with optional recent conversation history.

        - We pass `system_prompt` separately to the LLM service.
        - If `include_history` and `conversation_id` are provided, we prepend recent history.
        """
        try:
            sys_prompt = system_prompt or await self.get_system_prompt()
            payload: List[Dict[str, str]] = list(messages or [])

            if include_history and conversation_id:
                history = await self.get_conversation_history(conversation_id)
                if history:
                    # Prepend history (LLMService should handle total token limits)
                    payload = history + payload
                    self.logger.info(f"Injected {len(history)} history messages into LLM call")

            return await self.llm_service.generate_response(
                messages=payload,
                model=model,
                system_prompt=sys_prompt,
            )
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return "I ran into a problem generating a response. Please try again."
