"""
Multi-agent workflow for TaxFix system.
- Routes to one or more agents per turn.
- Executes them in order and merges outputs into a single assistant message.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
import asyncio

from ..core.state import AgentResponse, MessageRole, UserProfile, AgentType
from ..models.conversation import Conversation, Message, MessageType
from ..core.logging import get_logger
from ..agents.orchestrator import OrchestratorAgent
from ..agents.profile import ProfileAgent
from ..agents.tax_knowledge import TaxKnowledgeAgent
from ..agents.action_agent import ActionAgent
from ..agents.presenter import PresenterAgent
from ..services.llm import LLMService
from ..services.memory import MemoryService
from ..services.database import DatabaseService
from ..services.agent_router import AgentRouter, AgentPick
from ..tools.user_learning_tools import UserLearningTools
from ..tools.conversation_tools import ConversationTools

logger = get_logger(__name__)


class TaxFixWorkflow:
    """Multi-agent workflow for TaxFix system."""

    def __init__(
        self,
        llm_service: LLMService,
        memory_service: MemoryService,
        database_service: DatabaseService
    ):
        self.llm_service = llm_service
        self.memory_service = memory_service
        self.database_service = database_service

        # Intelligent router (multi-agent capable)
        self.agent_router = AgentRouter(llm_service)

        # Tools
        self.user_learning_tools = UserLearningTools(database_service, llm_service)
        self.conversation_tools = ConversationTools(database_service, llm_service)

        # Agents
        self.orchestrator = OrchestratorAgent(llm_service, memory_service, database_service)
        self.profile_agent = ProfileAgent(llm_service, memory_service, database_service)
        self.tax_knowledge_agent = TaxKnowledgeAgent(llm_service, memory_service, database_service)
        self.action_agent = ActionAgent(llm_service, memory_service, database_service)
        self.presenter_agent = PresenterAgent(llm_service, memory_service, database_service)

        logger.info("TaxFix workflow initialized (multi-agent)")

    # -------------------------
    # NOTE: Presenter Agent logic now handled by dedicated PresenterAgent class
    # -------------------------

    # -------------------------
    # Conversation helpers
    # -------------------------
    async def _ensure_conversation_exists(self, user_id: str, session_id: str) -> str:
        """Ensure conversation exists in database and return conversation ID."""
        try:
            existing = await self.database_service.get_user_conversations(user_id, limit=100)
            for conv in existing:
                if conv.id == session_id:
                    return conv.id

            conversation = Conversation(
                id=session_id,
                user_id=user_id,
                title=f"TaxFix Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                messages=[],
                context={},
                status="active",
            )
            created = await self.database_service.create_conversation(conversation)
            logger.info(f"Created conversation: {created.id}")
            return created.id
        except Exception as e:
            logger.error(f"Error ensuring conversation exists: {e}")
            return session_id

    async def _store_message_in_db(self, conversation_id: str, message: Message) -> None:
        """Store message in DB and cache in Redis."""
        try:
            await self.database_service.add_message(message)
            logger.info(f"Stored message {message.id} in conversation {conversation_id}")
            await self.memory_service.add_message_to_conversation_cache(conversation_id, message)
            logger.info(f"Cached message {message.id} in Redis for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error storing message: {e}")

    async def _get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent history (prefers Redis cache)."""
        try:
            cached = await self.memory_service.get_cached_conversation_history(conversation_id, limit)
            if cached:
                logger.info(f"Retrieved {len(cached)} msgs from Redis for {conversation_id}")
                return [{"role": (m.role.value if hasattr(m.role, "value") else m.role), "content": m.content} for m in cached]

            logger.info(f"Cache miss for {conversation_id}, fetching from DB")
            msgs = await self.database_service.get_conversation_messages(conversation_id, limit=limit)
            if msgs:
                await self.memory_service.cache_conversation_history(conversation_id, msgs)
            return [{"role": (m.role.value if hasattr(m.role, "value") else m.role), "content": m.content} for m in msgs]
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    # -------------------------
    # Core entry
    # -------------------------
    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        user_profile: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        """Process a user message through the multi-agent workflow."""
        logger.info(f"Processing message for session {session_id}")

        try:
            # Ensure conversation and persist user message
            conversation_id = await self._ensure_conversation_exists(user_id, session_id)
            user_msg = Message(
                id=f"msg_{int(time.time() * 1000)}",
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_message,
                message_type=MessageType.TEXT,
            )
            await self._store_message_in_db(conversation_id, user_msg)

            # Context & history
            conversation_context = await self.memory_service.get_conversation_context(session_id) or {}
            conversation_history = await self._get_conversation_history(conversation_id)

            context: Dict[str, Any] = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "conversation_stage": conversation_context.get("conversation_stage", "initial"),
                "previous_context": conversation_context,
                "message_count": conversation_context.get("message_count", 0) + 1,
                "conversation_history": conversation_history,
            }

            # Profile dict (lenient)
            user_profile_dict: Optional[Dict[str, Any]] = None
            if user_profile:
                user_profile_dict = user_profile.dict() if hasattr(user_profile, "dict") else (user_profile if isinstance(user_profile, dict) else None)

            # Followup override (kept for compat)
            force_profile = context.get("requires_followup") and context.get("missing_fields")

            # -------- Agent routing (multi) --------
            if force_profile:
                picks: List[AgentPick] = [AgentPick(agent="profile", confidence=0.95, reasons="followup-required", triggers=["followup"])]  # type: ignore
                logger.info("🔄 FORCE ROUTING: Profile agent required for followup")
            else:
                picks = await self.agent_router.select_agents(
                    user_message=user_message,
                    user_profile=user_profile_dict,
                    context=context,
                    conversation_history=conversation_history,
                )

            # Derive execution plan (names only, dedup while preserving order)
            plan: List[str] = []
            for p in picks:
                if p.agent not in plan:
                    plan.append(p.agent)

            logger.info(f"🧠 MULTI-AGENT ROUTING DECISION:")
            logger.info(f"   📊 Router picks: {[(p.agent, f'{p.confidence:.2f}', p.reasons) for p in picks]}")
            logger.info(f"   📋 Initial execution plan: {plan}")

            # If orchestrator is combined with specialized agents, skip it here.
            # We'll synthesize ourselves; run orchestrator only when it's alone.
            if "orchestrator" in plan and len(plan) > 1:
                plan = [a for a in plan if a != "orchestrator"]
                logger.info(f"   🎭 Removed orchestrator from multi-agent plan, final plan: {plan}")

            # Safety: default to orchestrator if plan empty
            if not plan:
                plan = ["orchestrator"]
                logger.info(f"   🔧 Fallback to orchestrator (empty plan)")

            logger.info(f"🚀 EXECUTING {len(plan)} AGENT(S): {plan}")

            # -------- Execute agents in sequence --------
            per_agent_results: List[Tuple[str, AgentResponse, float]] = []
            
            for i, agent_name in enumerate(plan, 1):
                logger.info(f"🎯 AGENT {i}/{len(plan)}: Starting {agent_name.upper()} agent")
                logger.info(f"   💬 Message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
                logger.info(f"   🧳 Context keys: {list(context.keys())}")
                if context.get("user_expenses"):
                    logger.info(f"   💰 Available expenses: {len(context['user_expenses'])} items, €{context['expense_summary']['total_amount']:.2f}")
                if context.get("user_tax_documents"):
                    logger.info(f"   📄 Available tax docs: {len(context['user_tax_documents'])} items")
                
                t0 = time.perf_counter()
                resp = await self._run_single_agent(
                    agent_name=agent_name,
                    user_message=user_message,
                    context=context,
                    session_id=session_id,
                    user_profile=user_profile_dict,
                )
                dt = time.perf_counter() - t0
                per_agent_results.append((agent_name, resp, dt))

                logger.info(f"✅ AGENT {i}/{len(plan)}: {agent_name.upper()} completed in {dt:.2f}s")
                logger.info(f"   📝 Response length: {len(resp.content)} chars")
                logger.info(f"   🎯 Confidence: {resp.confidence:.2f}")
                logger.info(f"   🔍 Reasoning: {resp.reasoning}")

                # Light context rolling: allow later agents to see previous outputs
                # (non-breaking: add under 'agent_outputs' so existing agents ignore safely)
                context.setdefault("agent_outputs", [])
                context["agent_outputs"].append({"agent": agent_name, "content": resp.content, "metadata": resp.metadata})
                
                if i < len(plan):
                    logger.info(f"🔄 CONTEXT HANDOFF: Passing results to next agent ({plan[i]})")
                    logger.info(f"   📊 Previous outputs count: {len(context['agent_outputs'])}")

            logger.info(f"🏁 MULTI-AGENT EXECUTION COMPLETE: {len(per_agent_results)} agents executed")

            # -------- Merge responses --------
            logger.info(f"🔗 MERGING RESPONSES: Combining {len(per_agent_results)} agent outputs")
            combined = await self._combine_agent_responses(per_agent_results, picks, user_message, context)
            logger.info(f"✨ FINAL RESPONSE: {len(combined.content)} chars, confidence {combined.confidence:.2f}")

            # Persist assistant message (single merged message)
            assistant_msg = Message(
                id=f"msg_{int(time.time() * 1000) + 1}",
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=combined.content,
                message_type=MessageType.TEXT,
            )
            await self._store_message_in_db(conversation_id, assistant_msg)

            # Update context + learning hooks
            await self._update_conversation_context(session_id, context, combined)
            await self._process_learning_and_updates(user_id, conversation_id, context, combined)

            # Execution metrics (simple)
            exec_metrics = {
                "agents_run": [n for n, _, _ in per_agent_results],
                "timings_s": {n: t for n, _, t in per_agent_results},
                "router_picks": [{"agent": p.agent, "confidence": p.confidence, "reasons": p.reasons} for p in picks],
            }

            return {
                "content": combined.content,
                "confidence": combined.confidence,
                "reasoning": combined.reasoning,
                "suggested_actions": combined.suggested_actions,
                "metadata": combined.metadata,
                "execution_metrics": exec_metrics,
                "conversation_id": conversation_id,
            }

        except Exception as e:
            logger.error(f"Workflow processing error: {e}")
            return {
                "content": "I apologize, but I encountered an error processing your request.",
                "confidence": 0.0,
                "reasoning": f"Workflow error: {e}",
                "suggested_actions": [],
                "metadata": {"error": str(e)},
                "execution_metrics": {},
            }

    # -------------------------
    # Agent execution & merge
    # -------------------------
    async def _run_single_agent(
        self,
        agent_name: str,
        user_message: str,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]],
    ) -> AgentResponse:
        """Run one agent by name."""
        msg = Message(
            id=f"msg_{int(time.time() * 1000)}",
            conversation_id=context["conversation_id"],
            role=MessageRole.USER,
            content=user_message,
            message_type=MessageType.TEXT,
        )

        if agent_name == "tax_knowledge":
            return await self.tax_knowledge_agent.process(msg, context, session_id, user_profile)
        if agent_name == "action":
            return await self.action_agent.process(msg, context, session_id, user_profile)
        if agent_name == "profile":
            return await self.profile_agent.process(msg, context, session_id, user_profile)
        # Fallback to orchestrator
        return await self.orchestrator.process(msg, context, session_id, user_profile)

    async def _combine_agent_responses(
        self,
        per_agent_results: List[Tuple[str, AgentResponse, float]],
        picks: List[AgentPick],
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        """Merge multiple AgentResponse objects into one."""
        logger.info(f"🔀 RESPONSE MERGE: Processing {len(per_agent_results)} agent results")
        
        if not per_agent_results:
            logger.warning("❌ No agent results to merge, returning error response")
            return AgentResponse(
                agent_type=AgentType.ORCHESTRATOR,  # <- required
                content="I couldn't determine which assistant should handle that. Could you rephrase?",
                confidence=0.0,
                reasoning="no-agent-results",
                suggested_actions=[],
                metadata={"agent_type": "multi", "merged": True},
            )

        # If only one, return as-is but enrich metadata (preserve the original agent_type)
        if len(per_agent_results) == 1:
            agent_name, resp, dt = per_agent_results[0]
            logger.info(f"📋 SINGLE AGENT RESPONSE: Using {agent_name} output directly")
            meta = dict(resp.metadata or {})
            meta.update({
                "agent_type": agent_name,  # keep a human-friendly tag alongside enum
                "merged": False,
                "runtime_s": {agent_name: dt},
                "router_picks": [{"agent": p.agent, "confidence": p.confidence} for p in picks],
            })
            return AgentResponse(
                agent_type=resp.agent_type,  # <- preserve source agent_type
                content=resp.content,
                confidence=resp.confidence,
                reasoning=resp.reasoning,
                suggested_actions=list(resp.suggested_actions or []),
                metadata=meta,
            )

        # TODO: Replace this with Presenter Agent for intelligent response synthesis
        # Otherwise, merge multiple (TEMPORARILY COMMENTED OUT - WILL BE REPLACED BY PRESENTER AGENT)
        """
        logger.info(f"🔧 MULTI-AGENT MERGE: Combining {len(per_agent_results)} responses")
        title_map = {
            "profile": "Profile updates & clarifications",
            "action": "Expenses & deductions captured",
            "tax_knowledge": "Tax analysis & optimization",
            "orchestrator": "General guidance",
        }
        lines: List[str] = []
        for agent_name, resp, _ in per_agent_results:
            section_title = title_map.get(agent_name, agent_name.replace("_", " ").title())
            if (resp.content or "").strip():
                logger.info(f"   📝 Adding section: {section_title} ({len(resp.content)} chars)")
                lines.append(f"## {section_title}")
                lines.append(resp.content.strip())
                lines.append("")

        merged_content = "\n".join(lines).strip()
        logger.info(f"✅ MERGED CONTENT: {len(merged_content)} total characters")
        """

        # Use Presenter Agent for intelligent response synthesis
        logger.info(f"🎨 PRESENTER AGENT: Synthesizing {len(per_agent_results)} agent outputs into cohesive response")
        merged_content = await self.presenter_agent.synthesize_responses(
            agent_results=per_agent_results,
            user_message=user_message,
            context=context
        )

        confidences = [max(0.0, min(1.0, r.confidence or 0.0)) for _, r, _ in per_agent_results]
        final_conf = max(confidences) if confidences else 0.0
        if len(per_agent_results) > 1:
            final_conf = max(0.0, min(1.0, final_conf - 0.05))  # tiny merge penalty

        reasons = []
        for name, r, _ in per_agent_results:
            if r.reasoning:
                reasons.append(f"{name}: {r.reasoning}")
        merged_reasoning = " | ".join(reasons)[:2000] if reasons else ""

        sugg: List[Any] = []
        seen = set()
        for _, r, _ in per_agent_results:
            for s in r.suggested_actions or []:
                key = str(s)
                if key not in seen:
                    sugg.append(s)
                    seen.add(key)

        final_meta: Dict[str, Any] = {"agent_type": "multi", "merged": True}
        runtimes: Dict[str, float] = {}
        profile_updated = False
        requires_followup = False
        missing_fields: List[str] = []

        for name, r, dt in per_agent_results:
            runtimes[name] = dt
            if r.metadata:
                for k, v in r.metadata.items():
                    if k == "profile_updated":
                        profile_updated = profile_updated or bool(v)
                    elif k == "requires_followup":
                        requires_followup = requires_followup or bool(v)
                    elif k == "missing_fields":
                        if isinstance(v, list):
                            for fld in v:
                                if fld not in missing_fields:
                                    missing_fields.append(fld)
                    else:
                        final_meta.setdefault(k, v)

        final_meta.update({
            "router_picks": [{"agent": p.agent, "confidence": p.confidence, "reasons": p.reasons} for p in picks],
            "runtime_s": runtimes,
            "per_agent": [
                {"agent": name, "confidence": r.confidence, "meta": (r.metadata or {})}
                for name, r, _ in per_agent_results
            ],
            "profile_updated": profile_updated,
            "requires_followup": requires_followup,
            "missing_fields": missing_fields,
        })

        return AgentResponse(
            agent_type=AgentType.ORCHESTRATOR,  # <- umbrella type for merged message
            content=merged_content or "Done.",
            confidence=final_conf,
            reasoning=merged_reasoning,
            suggested_actions=sugg,
            metadata=final_meta,
        )


    # -------------------------
    # Context + learning hooks
    # -------------------------
    async def _update_conversation_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        response: AgentResponse
    ) -> None:
        """Update conversation context in memory."""
        try:
            agent_type = response.metadata.get("agent_type", "unknown")
            if agent_type == "multi":
                # derive a compact last_agent hint
                seq = response.metadata.get("per_agent", [])
                last_agent = " + ".join([p.get("agent", "?") for p in seq])[:80] or "multi"
            else:
                last_agent = agent_type

            updates = {
                "conversation_stage": context.get("conversation_stage", "initial"),
                "message_count": context.get("message_count", 1),
                "last_agent": last_agent,
                "last_topic": self._extract_topic_from_response(response.content),
                "user_intent": response.metadata.get("user_intent"),
                "requires_followup": response.metadata.get("requires_followup", False),
                "missing_fields": response.metadata.get("missing_fields", []),
                "updated_at": datetime.utcnow().isoformat(),
            }
            await self.memory_service.update_conversation_context(session_id, updates)
            logger.info(f"Updated conversation context for session {session_id}")
        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")

    async def _process_learning_and_updates(
        self,
        user_id: str,
        conversation_id: str,
        context: Dict[str, Any],
        response: AgentResponse
    ) -> None:
        """Learning + profile updates."""
        try:
            msg_count = context.get("message_count", 1)

            # Update interaction count on user profile
            await self._update_user_interaction_count(user_id)

            # Trigger learning periodically or on profile update
            if (
                msg_count % 5 == 0
                or response.metadata.get("profile_updated", False)
                or response.metadata.get("requires_learning", False)
            ):
                logger.info(f"Processing learning for user {user_id}, conversation {conversation_id}")
                ok = await self.user_learning_tools.process_conversation_learning(user_id, conversation_id)
                if ok:
                    logger.info(f"Learning processed for user {user_id}")
                else:
                    logger.warning(f"Learning processing failed for user {user_id}")

            # Update auto-title near conversation start
            if msg_count <= 2:
                await self._update_conversation_title(conversation_id)

        except Exception as e:
            logger.error(f"Error in learning/updates: {e}")

    async def _update_user_interaction_count(self, user_id: str) -> None:
        try:
            profile = await self.database_service.get_user_profile(user_id)
            if profile:
                profile.conversation_count = (profile.conversation_count or 0) + 1
                profile.last_interaction = datetime.utcnow()
                await self.database_service.update_user_profile(profile)
                logger.info(f"Updated interaction count for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating user interaction count: {e}")

    async def _update_conversation_title(self, conversation_id: str) -> None:
        try:
            title = await self.conversation_tools.analyze_conversation_for_title(conversation_id)
            if title and title != "New Conversation":
                await self.database_service.update_conversation_title(conversation_id, title)
                logger.info(f"Updated conversation title: {title}")
        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")

    def _extract_topic_from_response(self, response_content: str) -> str:
        """Simple topic classifier (kept for speed/robustness)."""
        try:
            content_lower = (response_content or "").lower()
            if any(w in content_lower for w in ["tax", "liability", "calculation"]):
                return "tax_calculation"
            if any(w in content_lower for w in ["deduction", "expense", "credit"]):
                return "deductions"
            if any(w in content_lower for w in ["profile", "income", "status", "dependent"]):
                return "profile_update"
            if any(w in content_lower for w in ["hello", "help", "greeting"]):
                return "greeting"
            return "general_tax_advice"
        except Exception as e:
            logger.error(f"Error extracting topic: {e}")
            return "unknown"


# Backend entry
async def build_workflow():
    """Build and return the TaxFixWorkflow for backend API."""
    from ..services.llm import LLMService
    from ..services.memory import MemoryService
    from ..services.database import DatabaseService

    llm_service = LLMService()
    memory_service = MemoryService()
    database_service = DatabaseService()

    # Connect to Redis (best effort)
    try:
        await memory_service.connect()
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Memory service will work without Redis.")

    return TaxFixWorkflow(
        llm_service=llm_service,
        memory_service=memory_service,
        database_service=database_service,
    )
