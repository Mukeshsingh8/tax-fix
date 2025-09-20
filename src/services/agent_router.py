from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import re
import json

from ..core.logging import get_logger
from ..services.llm import LLMService

logger = get_logger(__name__)

# ------------------------------
# Models
# ------------------------------
class AgentPick(BaseModel):
    agent: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: str = ""
    triggers: List[str] = Field(default_factory=list)

# ------------------------------
# Router
# ------------------------------
class AgentRouter:
    """Intelligent agent router that can return multiple agents + confidences."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.logger = get_logger(__name__)

        self.agent_descriptions = {
            "tax_knowledge": {
                "name": "Tax Knowledge Agent",
                "description": "German tax calculations, liability, deductions, credits, optimization.",
                "capabilities": [
                    "Tax liability, social security contribution math",
                    "Deductions/credits identification",
                    "Tax optimization guidance",
                    "German law explanations",
                ],
                "use_cases": [
                    "What is my tax liability?",
                    "How much tax will I pay?",
                    "What deductions can I claim?",
                    "How to increase my refund?",
                    "Optimize my taxes",
                ],
            },
            "action": {
                "name": "Action Agent",
                "description": "Expense capture/confirmation/categorization and tracking.",
                "capabilities": [
                    "Detect deductible expenses",
                    "Add/confirm expenses",
                    "Categorize and track",
                ],
                "use_cases": [
                    "I bought a laptop for work",
                    "Add this as a business expense",
                    "Yes, add it",
                    "I have home office expenses",
                ],
            },
            "profile": {
                "name": "Profile Agent",
                "description": "User profile updates (income, status, dependents, preferences).",
                "capabilities": [
                    "Update profile fields",
                    "Extract personal/financial details from text",
                    "Confirm changes",
                ],
                "use_cases": [
                    "Update my income to €80,000",
                    "Change my filing status to married",
                    "I have 2 dependents",
                    "My name is John",
                ],
            },
            "orchestrator": {
                "name": "Orchestrator Agent",
                "description": "Greetings/general Q&A/glue. Coordinates others.",
                "capabilities": [
                    "Handle greetings",
                    "General info",
                    "Fallback / glue",
                ],
                "use_cases": [
                    "Hello",
                    "What can you do?",
                    "General questions",
                ],
            },
        }
        self.valid_agents = list(self.agent_descriptions.keys())

        # Heuristic keyword/regex triggers (lowercased comparison)
        self.rules = {
            "action_confirm": re.compile(
                r"\b(yes|yep|sure|please add|add it|go ahead|confirm|that's correct|thats correct)\b",
                re.I,
            ),
            "action_expense": re.compile(
                r"\b(bought|purchased|expense|receipt|invoice|ticket|fare|kurs|training|laptop|software|home[- ]?office|reise|commute|pendler|werkzeug|equipment)\b",
                re.I,
            ),
            "action_user_info": re.compile(
                r"\b(about me|my details|my information|my data|what do you know|my expenses|what i have|show me|list my|tell me about|summary|overview|expenses i|deductions i)\b",
                re.I,
            ),
            "profile_update": re.compile(
                r"\b(update|change|set|correct|adjust)\b.*\b(income|dependents?|filing status|status|name|email)\b|\b(my income is|i earn|i make)\b",
                re.I,
            ),
            "tax_knowledge": re.compile(
                r"\b(tax|refund|deduction|deduct|liability|optimi[sz]e|steu(er|ern)|werbungskosten|riester|rürup|anlage|elster|kinderfreibetrag)\b",
                re.I,
            ),
        }

        # Priority order when multiple agents are selected
        self.execution_order = ["profile", "action", "tax_knowledge", "orchestrator"]

        self.logger.info("AgentRouter initialized (multi-agent capable)")

    # ------------------------------
    # Public API (multi)
    # ------------------------------
    async def select_agents(
        self,
        user_message: str,
        user_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[AgentPick]:
        """
        Returns a prioritized list of agents to run with confidence + reasons.
        """
        # 1) Deterministic rules (strong signals)
        picks = self.rule_based_picks(user_message, conversation_history)

        # 2) LLM-scored structured picks
        llm_picks = await self.llm_scored_picks(user_message, user_profile, context, conversation_history)

        # 3) Merge + dedupe (keep max confidence per agent, merge reasons/triggers)
        merged: Dict[str, AgentPick] = {}
        for pick in picks + llm_picks:
            if pick.agent not in self.valid_agents:
                continue
            if pick.agent not in merged or pick.confidence > merged[pick.agent].confidence:
                merged[pick.agent] = pick
            else:
                if pick.reasons and pick.reasons not in merged[pick.agent].reasons:
                    merged[pick.agent].reasons += f" | {pick.reasons}"
                for t in pick.triggers:
                    if t not in merged[pick.agent].triggers:
                        merged[pick.agent].triggers.append(t)

        # 4) Fallback
        if not merged:
            merged["orchestrator"] = AgentPick(agent="orchestrator", confidence=0.5, reasons="fallback")

        # 5) Sort by execution order then confidence
        ordered = sorted(
            merged.values(),
            key=lambda p: (self.execution_order.index(p.agent) if p.agent in self.execution_order else 999, -p.confidence),
        )

        self.logger.info("Routing picks: " + ", ".join([f"{p.agent}@{p.confidence:.2f}" for p in ordered]))
        return ordered

    # ------------------------------
    # Public API (single, backward compatible)
    # ------------------------------
    async def select_agent(
        self,
        user_message: str,
        user_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        picks = await self.select_agents(user_message, user_profile, context, conversation_history)
        top = picks[0] if picks else AgentPick(agent="orchestrator", confidence=0.5, reasons="fallback")
        self.logger.info(f"Top agent: {top.agent} ({top.confidence:.2f})")
        return top.agent

    # ------------------------------
    # Rule engine
    # ------------------------------
    def rule_based_picks(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[AgentPick]:
        text = user_message or ""
        picks: List[AgentPick] = []

        # Strong conversation-confirmation rule
        last_assistant = ""
        if conversation_history:
            for m in reversed(conversation_history):
                if m.get("role") == "assistant":
                    last_assistant = (m.get("content") or "").lower()
                    break

        if last_assistant and ("add this expense" in last_assistant or "should i add" in last_assistant or "add it?" in last_assistant):
            if self.rules["action_confirm"].search(text):
                picks.append(AgentPick(agent="action", confidence=0.95, reasons="user confirmed expense", triggers=["expense_confirmation"]))

        # User asking for their personal information → ACTION (high priority)
        if self.rules["action_user_info"].search(text):
            picks.append(AgentPick(agent="action", confidence=0.85, reasons="user requesting personal info/expenses", triggers=["user_info_request"]))

        # Direct expense mentions → ACTION
        if self.rules["action_expense"].search(text):
            picks.append(AgentPick(agent="action", confidence=0.8, reasons="expense-related phrasing", triggers=["expense_detected"]))

        # Profile update cues → PROFILE
        if self.rules["profile_update"].search(text):
            picks.append(AgentPick(agent="profile", confidence=0.75, reasons="profile update phrasing", triggers=["profile_update"]))

        # Tax knowledge cues → TAX_KNOWLEDGE
        if self.rules["tax_knowledge"].search(text):
            picks.append(AgentPick(agent="tax_knowledge", confidence=0.7, reasons="tax topic detected", triggers=["tax_query"]))

        # Greetings fallback
        if re.search(r"\b(hello|hi|hey|hallo|guten tag)\b", text, re.I) and not picks:
            picks.append(AgentPick(agent="orchestrator", confidence=0.6, reasons="greeting", triggers=["greeting"]))

        return picks

    # ------------------------------
    # LLM scoring (now uses generate_response + robust JSON parsing)
    # ------------------------------
    async def llm_scored_picks(
        self,
        user_message: str,
        user_profile: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> List[AgentPick]:
        # Prepare compact history
        hist = ""
        if conversation_history:
            tail = conversation_history[-6:]
            hist = "\n".join([f"- {m.get('role','?')}: {(m.get('content') or '')[:200]}" for m in tail])

        prompt = f"""
You are a router for a German tax assistant. Score EACH agent for the current user message.

Return JSON with this exact shape and keys only:
{{
  "agents": [
    {{"agent":"tax_knowledge","confidence":0.0,"reasons":"", "triggers":[]}},
    {{"agent":"action","confidence":0.0,"reasons":"", "triggers":[]}},
    {{"agent":"profile","confidence":0.0,"reasons":"", "triggers":[]}},
    {{"agent":"orchestrator","confidence":0.0,"reasons":"", "triggers":[]}}
  ]
}}

Rules:
- confidence ∈ [0,1]
- If the message includes both expense details and a tax question, BOTH "action" and "tax_knowledge" should have >0.5
- If the user intends to update personal info, "profile" should have >0.5
- If the user is asking the information about themself ALL "action" and "tax_knowledge" and "profile" should have >0.5
- Keep reasons short. No extra text outside the JSON.

Conversation context (last 6):
{hist or "n/a"}

User profile (summary):
{(user_profile or {})}

Current user message:
\"\"\"{user_message}\"\"\"
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            raw = await self.llm_service.generate_response(
                messages=messages,
                model="groq",
                system_prompt="Return strictly valid JSON only. No markdown. No prose.",
            )
            data = self.extract_first_json_object(raw)
            if not isinstance(data, dict) or "agents" not in data or not isinstance(data["agents"], list):
                raise ValueError("LLM did not return the expected JSON object")

            picks: List[AgentPick] = []
            for item in data.get("agents", []):
                agent = str(item.get("agent", "")).strip().lower()
                if agent in self.valid_agents:
                    try:
                        conf = float(item.get("confidence", 0.0))
                    except Exception:
                        conf = 0.0
                    reasons = str(item.get("reasons", ""))
                    triggers = item.get("triggers") or []
                    if not isinstance(triggers, list):
                        triggers = []
                    picks.append(AgentPick(agent=agent, confidence=max(0.0, min(1.0, conf)), reasons=reasons, triggers=list(triggers)))
            return picks

        except Exception as e:
            self.logger.warning(f"LLM scored picks parse failed: {e}")
            # Soft fallback: nudge tax_knowledge if taxy, else orchestrator
            fallback: List[AgentPick] = []
            if self.rules["tax_knowledge"].search(user_message or ""):
                fallback.append(AgentPick(agent="tax_knowledge", confidence=0.55, reasons="fallback:taxy"))
            else:
                fallback.append(AgentPick(agent="orchestrator", confidence=0.5, reasons="fallback"))
            return fallback

    # ------------------------------
    # JSON extraction helper
    # ------------------------------
    def extract_first_json_object(self, text: str) -> Any:
        """
        Extract the first top-level JSON object from a string and parse it.
        Handles extra prose by scanning braces while respecting strings/escapes.
        """
        if not text:
            raise ValueError("empty LLM response")

        # Fast path: try direct load
        try:
            return json.loads(text)
        except Exception:
            pass

        # Scan for first balanced {...}
        in_string = False
        escape = False
        depth = 0
        start = -1

        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch in ('"', "'"):
                # toggle only if not already in a string of the other quote? Keep it simple: treat both as toggles.
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            # continue scanning in case there is another well-formed object later
                            start = -1
                            continue

        raise ValueError("no JSON object found in LLM response")

    # (Utility accessors unchanged)
    def get_agent_description(self, agent_name: str) -> Optional[Dict[str, Any]]:
        return self.agent_descriptions.get(agent_name)

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        return self.agent_descriptions.copy()

    def add_agent(self, agent_name: str, description: Dict[str, Any]) -> bool:
        required = ["name", "description", "capabilities", "use_cases"]
        if not all(k in description for k in required):
            self.logger.error(f"Agent description missing keys: {required}")
            return False
        self.agent_descriptions[agent_name] = description
        if agent_name not in self.valid_agents:
            self.valid_agents.append(agent_name)
        self.logger.info(f"Added new agent: {agent_name}")
        return True

    def remove_agent(self, agent_name: str) -> bool:
        if agent_name not in self.agent_descriptions:
            self.logger.warning(f"Agent {agent_name} not found")
            return False
        del self.agent_descriptions[agent_name]
        if agent_name in self.valid_agents:
            self.valid_agents.remove(agent_name)
        self.logger.info(f"Removed agent: {agent_name}")
        return True

    def update_agent_description(self, agent_name: str, updates: Dict[str, Any]) -> bool:
        if agent_name not in self.agent_descriptions:
            self.logger.error(f"Agent {agent_name} not found")
            return False
        self.agent_descriptions[agent_name].update(updates)
        self.logger.info(f"Updated agent description: {agent_name}")
        return True
