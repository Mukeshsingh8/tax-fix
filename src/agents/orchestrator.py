"""Orchestrator agent for providing general responses and fallback handling."""

from typing import Dict, Optional, Any

from ..core.state import Message, AgentResponse, AgentType
from ..utils import safe_agent_method
from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    General response agent that handles simple queries and provides fallback responses.
    
    This agent is used when:
    - Simple greetings that don't need specialist knowledge
    - General tax questions that don't require specific agent expertise
    - Fallback when other agents fail or aren't appropriate
    
    Note: Agent routing is handled by AgentRouter service, not this agent.
    """

    def __init__(self, llm_service, memory_service, database_service, logger=None):
        super().__init__(AgentType.ORCHESTRATOR, llm_service, memory_service, database_service)

    @safe_agent_method(
        fallback_content="I can help with German tax questions. What would you like to know?",
        fallback_confidence=0.5
    )
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Process user message with general German tax assistance.
        
        This agent provides direct responses for:
        - Simple greetings
        - General tax questions
        - Information that doesn't need specialist agents
        """
        text = (message.content or "").strip()
        if not text:
            return await self.create_response(
                content="I can help with German tax questions. What would you like to know?",
                confidence=0.5,
                metadata={"response_type": "empty_input"}
            )

        # Determine response type based on message content
        if self._is_simple_greeting(text):
            return await self._create_greeting_response(text, user_profile)
        else:
            return await self._create_general_response(text, user_profile)

    def _is_simple_greeting(self, text: str) -> bool:
        """Check if message is a simple greeting."""
        text_lower = text.lower().strip()
        greetings = ['hi', 'hello', 'hey', 'hola', 'good morning', 'good afternoon', 'good evening']
        return any(greeting in text_lower for greeting in greetings) and len(text_lower.split()) <= 3

    async def _create_greeting_response(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> AgentResponse:
        """Create simple greeting response."""
        name = user_profile.get("name") if user_profile else None
        
        if name:
            content = f"Hi {name}! I'm here to help with your German tax questions. What can I do for you?"
        else:
            content = "Hi! I'm your German tax assistant. How can I help you today?"
        
        return await self.create_response(
            content=content,
            confidence=0.95,
            metadata={"response_type": "greeting"}
        )

    async def _create_general_response(self, text: str, user_profile: Optional[Dict[str, Any]]) -> AgentResponse:
        """Create general response for tax questions."""
        profile_context = ""
        if user_profile:
            profile_context = f"\nUser profile: {user_profile}"
        
        prompt = f"""Answer this German tax question briefly (2-3 sentences max) in English.
Use German tax terms with quick English explanations when helpful.
Be helpful but concise. Never recommend consulting a human professional.

Question: "{text}"{profile_context}

Answer:"""

        try:
            content = await self.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq"
            )
            
            return await self.create_response(
                content=content.strip(),
                confidence=0.7,
                metadata={"response_type": "general_answer", "source": "orchestrator_llm"}
            )
        except Exception as e:
            self.logger.error(f"LLM response generation failed: {e}")
            # Simple fallback without LLM
            fallback = "I can help with German tax questions like deductions, allowances, or tax calculations. What specific topic interests you?"
            
            return await self.create_response(
                content=fallback,
                confidence=0.5,
                metadata={"response_type": "fallback", "error": str(e)}
            )