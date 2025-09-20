"""Orchestrator agent for managing conversation flow."""

from typing import Dict, List, Optional, Any

from ..core.state import Message, AgentResponse, AgentType, UserProfile  # noqa: F401 (UserProfile used for typing)
from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrates the conversation by routing messages to the right specialist agents.

    Design principles:
    - Keep orchestration thin: detect intent -> call the right agent -> return its response.
    - Do NOT duplicate specialist logic (profile extraction, tax reasoning, clarifying Qs).
    - Always answer in English, but you may use German tax terms with brief English context.
    - Never recommend consulting a human professional.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.ORCHESTRATOR, *args, **kwargs)
        # Optional: external code can set either of these for resolving agents
        # self.resolve_agent = Callable[[str], Any]
        # self.agent_registry = Dict[str, Any]

    async def get_system_prompt(self) -> str:
        return (
            "You are the Orchestrator for a German tax assistant. "
            "Your job is to route the user's request to the correct specialist agent, "
            "ensure answers are concise and in English, and avoid non-tax chit-chat. "
            "Use German tax terms (e.g., Werbungskosten) with short English explanations."
        )

    # ---------------------------
    # Entry point
    # ---------------------------
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        try:
            # Basic sanity
            if not message or not (message.content or "").strip():
                return await self.create_response(
                    content="I didn’t receive a valid message. Could you rephrase your question?",
                    confidence=0.0,
                )

            # Ensure we have a profile dict (if one exists)
            if not user_profile and context.get("user_id"):
                fetched = await self.database_service.get_user_profile(context["user_id"])
                if fetched:
                    try:
                        user_profile = fetched.dict()
                    except Exception:
                        user_profile = dict(fetched)

            text = (message.content or "").strip()

            # 1) Greetings → quick, helpful greeting
            if self._is_greeting(text):
                return await self._greeting(user_profile)

            # 2) Explicit profile requests/updates → ProfileAgent
            if self._is_profile_query(text) or self._looks_like_profile_update(text):
                resp = await self._route_to_agent(
                    agent_name="profile",
                    message=message,
                    context=context,
                    session_id=session_id,
                    user_profile=user_profile,
                )
                if resp:
                    return resp

            # 3) Everything tax-content → TaxKnowledgeAgent
            resp = await self._route_to_agent(
                agent_name="tax_knowledge",
                message=message,
                context=context,
                session_id=session_id,
                user_profile=user_profile,
            )
            if resp:
                return resp

            # 4) Fallback (should rarely happen)
            return await self._fallback_direct_answer(message, user_profile, context)

        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            return await self.create_response(
                content="Sorry—something went wrong while handling your request. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    # ---------------------------
    # Agent resolution & routing
    # ---------------------------
    def _resolve_agent_instance(self, agent_name: str, context: Dict[str, Any]) -> Optional[Any]:
        """
        Resolve an agent instance using simplified resolution.
        
        Tries context registry first, then falls back to resolver function.
        """
        # Check context registry/agents dict
        for key in ("agent_registry", "agents"):
            reg = context.get(key)
            if isinstance(reg, dict) and agent_name in reg:
                return reg[agent_name]

        # Try context resolver function
        resolver = context.get("resolve_agent")
        if callable(resolver):
            try:
                return resolver(agent_name)
            except Exception as e:
                self.logger.warning(f"Agent resolution failed for '{agent_name}': {e}")

        return None

    async def _route_to_agent(
        self,
        agent_name: str,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]],
    ) -> Optional[AgentResponse]:
        """Fetch an agent via DI and delegate the request."""
        try:
            agent = self._resolve_agent_instance(agent_name, context)
            if not agent:
                self.logger.warning(f"Agent '{agent_name}' not available (no registry/instance provided).")
                return None

            return await agent.process(
                message=message,
                context=context,
                session_id=session_id,
                user_profile=user_profile,
            )
        except Exception as e:
            self.logger.error(f"Routing to '{agent_name}' failed: {e}")
            return None

    # ---------------------------
    # Heuristics
    # ---------------------------
    def _is_greeting(self, text: str) -> bool:
        t = text.lower().strip("!?. ")
        return t in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"} or t.startswith(
            ("hi ", "hello ", "hey ")
        )

    def _is_profile_query(self, text: str) -> bool:
        t = text.lower()
        return any(
            kw in t
            for kw in [
                "my profile",
                "my information",
                "what do you know about me",
                "my details",
                "my data",
                "annual income",
                "filing status",
                "dependents",
            ]
        )

    def _looks_like_profile_update(self, text: str) -> bool:
        """Check if text looks like a profile update request."""
        import re
        t = text.lower()
        
        # Direct update keywords
        update_keywords = ["update", "change", "correct", "modify", "actually", "wrong"]
        if any(word in t for word in update_keywords):
            return True
            
        # Income/salary patterns
        income_patterns = [
            r"\b(income|salary|earn|make|ctc)\s*.*?\d",
            r"\b\d[\d,\.]*\s?(€|eur|k|thousand)\b"
        ]
        return any(re.search(pattern, t) for pattern in income_patterns)

    # ---------------------------
    # Small responses
    # ---------------------------
    async def _greeting(self, user_profile: Optional[Dict[str, Any]]) -> AgentResponse:
        if not user_profile:
            return await self.create_response(
                content=(
                    "Hello! I’m your German tax assistant. "
                    "Ask me about deductions (Werbungskosten), special expenses (Sonderausgaben), tax classes, "
                    "or a quick 2024 tax/net-income estimate. How can I help today?"
                ),
                confidence=0.95,
                metadata={"greeting": True},
            )

        name = user_profile.get("name") or "there"
        filing = (user_profile.get("filing_status") or "single").replace("_", " ").title()
        deps = user_profile.get("dependents", 0)
        income = user_profile.get("annual_income")
        income_str = f"€{income:,.2f}" if isinstance(income, (int, float)) else "—"

        text = (
            f"Hello {name}! I can tailor answers to your profile "
            f"(filing status: {filing}, dependents: {deps}, income: {income_str}). "
            "What would you like to explore—eligible deductions, a quick tax/benefits breakdown, or something else?"
        )
        return await self.create_response(content=text, confidence=0.95, metadata={"greeting": True})

    async def _fallback_direct_answer(
        self, message: Message, user_profile: Optional[Dict[str, Any]], context: Dict[str, Any]
    ) -> AgentResponse:
        """Small LLM fallback when a specialist agent isn't available."""
        try:
            profile_text = (
                f"Profile: {user_profile}"
                if user_profile
                else "Profile: (not available). If the answer needs income/filing status, ask briefly."
            )
            prompt = f"""
Answer the user's German tax question briefly (max 3 sentences), in English.
Use German tax terms with quick English hints when useful.
Never recommend a human professional or meetings.

Question: "{message.content}"
{profile_text}
"""
            resp = await self.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=True,
            )
            return await self.create_response(
                content=resp,
                reasoning="Fallback direct answer (no specialist agent available).",
                confidence=0.7,
                metadata={"fallback": True},
            )
        except Exception as e:
            self.logger.error(f"Fallback direct answer failed: {e}")
            return await self.create_response(
                content="I can help with German tax questions like deductions, child allowance, or a quick net-income estimate.",
                confidence=0.5,
            )
