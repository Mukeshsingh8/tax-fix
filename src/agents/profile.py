"""Profile agent for managing user profiles and personalization."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from ..core.state import Message, AgentResponse, AgentType
from ..models.user import EmploymentStatus, FilingStatus, UserProfile
from .base import BaseAgent
from ..core.helpers import extract_numbers  # keep your helper


class ProfileAgent(BaseAgent):
    """Profile agent that manages user profiles and personalization."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.PROFILE, *args, **kwargs)

    async def get_system_prompt(self) -> str:
        return """
        You are the Profile Agent for the TaxFix system. Your role is to:
        1) Extract and update user profile information (income, filing status, dependents, employment status, preferences)
        2) Ask clarifying questions when info is incomplete
        3) Learn user preferences (goals, risk tolerance, style)
        4) Provide personalized next steps
        IMPORTANT:
        - Always respond in English.
        - Prefer concrete, structured updates over long prose.
        - Keep suggestions actionable.
        """

    # -----------------------------
    # Main entry
    # -----------------------------
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        try:
            user_id = context.get("user_id")
            if not user_id:
                return await self.create_response(
                    content="I need to know who you are to update your profile.",
                    confidence=0.0
                )

            current_profile = await self.database_service.get_user_profile(user_id)

            # If this is a follow-up to requested fields, handle that path first
            if context.get("requires_followup") and context.get("missing_fields"):
                return await self._handle_clarifying_response(message, current_profile, context, user_id)

            # If the user is asking about their profile (read/query), answer that
            if self._is_profile_query(message.content):
                return await self._handle_profile_query(message, current_profile, context)

            # Otherwise, try to extract updates from the message
            updates = await self._extract_profile_information(message, current_profile, context)

            if updates:
                norm = self._normalize_updates(updates)
                updated = await self._persist_profile(current_profile, norm, user_id)

                # Cache updated profile for fast access
                await self.memory_service.cache_user_profile(user_id, updated)

                summary = self._format_profile_summary(updated)
                return await self.create_response(
                    content=f"Got it — I’ve updated your profile. Here’s what I have now:\n\n{summary}",
                    reasoning=f"Extracted and updated: {list(norm.keys())}",
                    confidence=0.9,
                    suggested_actions=[
                        {"action": "review_profile", "description": "Review your updated profile"},
                        {"action": "complete_profile", "description": "Answer a few questions to fill gaps"},
                        {"action": "tax_ideas", "description": "See tax ideas based on your profile"}
                    ],
                    metadata={"profile_updated": True, "profile_updates": norm}
                )

            # No updates found → suggest targeted questions
            questions = self._suggest_profile_questions(current_profile)
            return await self.create_response(
                content=(
                    "I didn’t detect new profile information in your message. "
                    "Would you like to share a few details so I can personalize advice?"
                ),
                reasoning="No clear profile updates extracted",
                confidence=0.7,
                suggested_actions=[
                    {"action": "answer_questions", "description": "Answer profile questions", "questions": questions}
                ],
                metadata={"requires_followup": True, "missing_fields": self._missing_fields(current_profile)}
            )

        except Exception as e:
            self.logger.error(f"ProfileAgent.process error: {e}")
            return await self.create_response(
                content="I ran into an issue updating your profile. Could you try again?",
                confidence=0.0,
                reasoning=f"Error: {str(e)}"
            )

    # -----------------------------
    # Extraction (LLM + fallback)
    # -----------------------------
    async def _extract_profile_information(
        self,
        message: Message,
        current_profile: Optional[UserProfile],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLMService.generate_json to extract structured updates.
        Returns a dict with any of:
          employment_status, filing_status, annual_income, dependents,
          tax_goals (list[str]), risk_tolerance, age, health_insurance_type
        """
        # Build compact context (last 10 messages)
        history = context.get("conversation_history") or []
        tail = history[-10:]
        hist_text = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in tail]) or "n/a"

        user_prompt = f"""
Extract profile updates from the user message.

Allowed keys and values (only output these if present):
- employment_status: one of ["employed","self_employed","unemployed","retired","student"]
- filing_status: one of ["single","married_joint","married_separate","head_of_household","qualifying_widow"]
- annual_income: number (euros); if a range is mentioned, pick a single most likely value
- dependents: integer (>= 0)
- tax_goals: array of strings (e.g., ["maximize_deductions","maximize_refund","reduce_tax_liability"])
- risk_tolerance: one of ["conservative","moderate","aggressive"]
- age: integer (optional)
- health_insurance_type: one of ["statutory","private"] (optional)

Constraints:
- If nothing relevant, return {{}}
- Prefer explicit mentions over guesses
- Keep numbers plain (no commas or currency symbols)
- Output strictly a single JSON object with only the allowed keys above (omit unknown keys). No prose, no code fences.

Conversation (recent):
{hist_text}

Current profile (summary, for context only):
{{
  "employment_status": %(emp)s,
  "filing_status": %(fil)s,
  "annual_income": %(inc)s,
  "dependents": %(dep)s
}}

User message:
\"\"\"{message.content}\"\"\"
""".strip() % {
            "emp": getattr(current_profile, "employment_status", None),
            "fil": getattr(current_profile, "filing_status", None),
            "inc": getattr(current_profile, "annual_income", None),
            "dep": getattr(current_profile, "dependents", None),
        }

        try:
            messages = [
                {"role": "system", "content": "Return strictly valid, compact JSON only. No commentary or code fences."},
                {"role": "user", "content": user_prompt},
            ]
            data = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if v not in (None, "", [])}
            return {}
        except Exception as e:
            self.logger.warning(f"LLM JSON extraction failed, using fallback. Error: {e}")
            return await self._extract_profile_information_fallback(message, current_profile)


    async def _extract_profile_information_fallback(
        self,
        message: Message,
        current_profile: Optional[UserProfile]
    ) -> Dict[str, Any]:
        """Very simple, heuristic fallback extraction."""
        updates: Dict[str, Any] = {}
        text = message.content.lower()

        # Income
        nums = extract_numbers(message.content)  # your helper
        if nums and any(w in text for w in ["income", "salary", "earn", "make", "annual"]):
            updates["annual_income"] = max(nums)

        # Filing status
        if "head of household" in text:
            updates["filing_status"] = "head_of_household"
        elif "married" in text:
            updates["filing_status"] = "married_joint" if "joint" in text else "married_separate"
        elif "single" in text:
            updates["filing_status"] = "single"

        # Dependents
        dep_match = re.search(r"(\d+)\s*(?:dependents?|children?|kids?)", text)
        if dep_match:
            try:
                updates["dependents"] = max(0, int(dep_match.group(1)))
            except Exception:
                pass

        # Employment
        if "self-employed" in text or "self employed" in text or "freelance" in text:
            updates["employment_status"] = "self_employed"
        elif "student" in text:
            updates["employment_status"] = "student"
        elif "retired" in text:
            updates["employment_status"] = "retired"
        elif "unemployed" in text:
            updates["employment_status"] = "unemployed"
        elif "employed" in text or "job" in text or "work at" in text:
            updates["employment_status"] = "employed"

        return updates

    # -----------------------------
    # Normalize + persist
    # -----------------------------
    def _normalize_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Map synonyms to enum values, clamp numbers, strip strings."""
        from ..utils import (
            normalize_employment_status,
            normalize_filing_status,
            normalize_risk_tolerance,
            normalize_tax_goals,
            safe_float,
            safe_int,
        )
        
        norm: Dict[str, Any] = {}

        # Normalize each field using utility functions
        if "employment_status" in updates:
            normalized_emp = normalize_employment_status(updates["employment_status"])
            if normalized_emp:
                norm["employment_status"] = normalized_emp

        if "filing_status" in updates:
            normalized_filing = normalize_filing_status(updates["filing_status"])
            if normalized_filing:
                norm["filing_status"] = normalized_filing

        if "annual_income" in updates:
            normalized_income = safe_float(updates["annual_income"])
            if normalized_income is not None:
                norm["annual_income"] = normalized_income

        if "dependents" in updates:
            normalized_deps = safe_int(updates["dependents"])
            if normalized_deps is not None:
                norm["dependents"] = normalized_deps

        if "tax_goals" in updates:
            normalized_goals = normalize_tax_goals(updates["tax_goals"])
            if normalized_goals:
                norm["tax_goals"] = normalized_goals

        if "risk_tolerance" in updates:
            normalized_risk = normalize_risk_tolerance(updates["risk_tolerance"])
            if normalized_risk:
                norm["risk_tolerance"] = normalized_risk

        if "age" in updates:
            normalized_age = safe_int(updates["age"])
            if normalized_age is not None:
                norm["age"] = normalized_age

        # Health insurance type (simple validation)
        if "health_insurance_type" in updates:
            hi = str(updates["health_insurance_type"]).strip().lower()
            if hi in ("statutory", "private"):
                norm["health_insurance_type"] = hi

        return norm

    async def _persist_profile(
        self,
        current_profile: Optional[UserProfile],
        updates: Dict[str, Any],
        user_id: str
    ) -> UserProfile:
        """Create or update profile in DB, returning the saved object."""
        if current_profile:
            # Update existing
            for k, v in updates.items():
                if hasattr(current_profile, k):
                    setattr(current_profile, k, v)
            current_profile.updated_at = datetime.utcnow()
            saved = await self.database_service.update_user_profile(current_profile)
            return saved
        else:
            # Create new with sane defaults + updates
            payload = {
                "user_id": user_id,
                "employment_status": updates.get("employment_status"),
                "filing_status": updates.get("filing_status") or "single",
                "annual_income": updates.get("annual_income"),
                "dependents": updates.get("dependents", 0),
                "preferred_deductions": [],
                "tax_goals": updates.get("tax_goals", []),
                "risk_tolerance": updates.get("risk_tolerance", "conservative"),
                "conversation_count": 0,
                "last_interaction": datetime.utcnow(),
                "preferred_communication_style": "friendly",
                "frequently_asked_questions": [],
                "common_expenses": [],
                "tax_complexity_level": "beginner",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            new_prof = UserProfile(**payload)
            saved = await self.database_service.create_user_profile(new_prof)
            return saved

    # -----------------------------
    # Queries / Clarifications
    # -----------------------------
    def _is_profile_query(self, message_content: str) -> bool:
        content_lower = message_content.lower()
        keywords = [
            "what is my", "my income", "my profile", "my information",
            "annual income", "filing status", "dependents", "my situation",
            "what do you know about me", "my details", "my data", "what do you have on me"
        ]
        return any(k in content_lower for k in keywords)

    async def _handle_profile_query(
        self,
        message: Message,
        current_profile: Optional[UserProfile],
        context: Dict[str, Any]
    ) -> AgentResponse:
        try:
            if not current_profile:
                return await self.create_response(
                    content=(
                        "I don’t have your profile yet. Want to personalize advice? "
                        "You can share your annual income, filing status, and any dependents."
                    ),
                    reasoning="No profile on file",
                    confidence=0.8,
                    suggested_actions=[
                        {"action": "provide_income", "description": "Share your annual income"},
                        {"action": "provide_filing_status", "description": "Share your filing status"},
                        {"action": "provide_dependents", "description": "Share number of dependents"},
                    ],
                    metadata={"profile_queried": True, "has_profile": False}
                )

            # Build a short, personalized summary using the stored values
            summary = self._format_profile_summary(current_profile)

            # Optionally embellish with LLM (kept short & contextual)
            history = context.get("conversation_history") or []
            tail = history[-10:]
            hist_text = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in tail]) or "n/a"
            prompt = f"""
User asked about their profile. Compose a warm, concise answer referencing the facts below and, if helpful, recent conversation context. Avoid restating every field; be helpful and brief.

Facts:
{summary}

Recent conversation context:
{hist_text}

User message:
\"\"\"{message.content}\"\"\"
""".strip()

            personalized = await self.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=False,
                system_prompt="Be concise, friendly, and specific. 3–4 sentences max."
            )

            return await self.create_response(
                content=personalized,
                reasoning="Personalized profile summary",
                confidence=0.9,
                suggested_actions=[
                    {"action": "update_profile", "description": "Update profile information"},
                    {"action": "analyze_tax_situation", "description": "Analyze tax situation"},
                    {"action": "identify_deductions", "description": "Identify potential deductions"},
                ],
                metadata={"profile_queried": True, "has_profile": True}
            )
        except Exception as e:
            self.logger.error(f"_handle_profile_query error: {e}")
            return await self.create_response(
                content="I can help you with your profile. Would you like to share your income, filing status, or dependents?",
                confidence=0.5,
                reasoning=f"Error: {str(e)}"
            )

    async def _handle_clarifying_response(
        self,
        message: Message,
        current_profile: Optional[UserProfile],
        context: Dict[str, Any],
        user_id: str
    ) -> AgentResponse:
        try:
            updates = await self._extract_profile_information(message, current_profile, context)
            if updates:
                norm = self._normalize_updates(updates)
                saved = await self._persist_profile(current_profile, norm, user_id)
                await self.memory_service.cache_user_profile(user_id, saved)

                missing_before = context.get("missing_fields", [])
                remaining = self._missing_fields(saved)

                if remaining:
                    return await self.create_response(
                        content=(
                            "Great—I've updated your profile. I still need a bit more to personalize fully: "
                            + ", ".join(remaining)
                        ),
                        reasoning=f"Updated some fields; still missing {remaining}",
                        confidence=0.85,
                        suggested_actions=[
                            {"action": "provide_more_info", "description": "Provide the remaining information"},
                            {"action": "get_general_guidance", "description": "Get general guidance now"}
                        ],
                        metadata={
                            "profile_updated": True,
                            "remaining_missing": remaining,
                            "requires_followup": True
                        }
                    )
                else:
                    return await self.create_response(
                        content="Perfect—your profile is complete. Ready for personalized tax guidance.",
                        reasoning="All required fields present",
                        confidence=0.92,
                        suggested_actions=[
                            {"action": "get_personalized_guidance", "description": "Get personalized tax guidance"},
                            {"action": "review_profile", "description": "Review your full profile"}
                        ],
                        metadata={"profile_updated": True, "profile_complete": True}
                    )

            # No usable info
            return await self.create_response(
                content=(
                    "I didn’t catch those details. For example, you can say ‘My income is €50,000’ "
                    "or ‘I’m single’."
                ),
                reasoning="No fields extracted in clarifying reply",
                confidence=0.6,
                suggested_actions=[
                    {"action": "provide_info_again", "description": "Provide the requested information"},
                    {"action": "get_general_guidance", "description": "Continue without full profile"}
                ],
                metadata={"requires_followup": True, "clarification_needed": True}
            )
        except Exception as e:
            self.logger.error(f"_handle_clarifying_response error: {e}")
            return await self.create_response(
                content="Something went wrong while processing that. Could you try again?",
                confidence=0.0,
                reasoning=f"Error: {str(e)}"
            )

    # -----------------------------
    # Utilities
    # -----------------------------
    def _format_profile_summary(self, profile: UserProfile) -> str:
        from ..utils import format_currency, val_to_str
        
        income = format_currency(profile.annual_income)
        filing = (val_to_str(profile.filing_status) or "single").replace("_", " ").title()
        dependents = profile.dependents or 0
        employment = (val_to_str(profile.employment_status) or "not specified").replace("_", " ").title()
        last = profile.last_interaction.strftime("%Y-%m-%d") if profile.last_interaction else "Never"
        return (
            f"- Annual income: {income}\n"
            f"- Filing status: {filing}\n"
            f"- Dependents: {dependents}\n"
            f"- Employment status: {employment}\n"
            f"- Last updated: {last}"
        )

    def _missing_fields(self, profile: Optional[UserProfile]) -> List[str]:
        required = ["annual_income", "filing_status", "dependents", "employment_status"]
        if not profile:
            return required
        missing: List[str] = []
        if not profile.annual_income and profile.annual_income != 0:
            missing.append("annual_income")
        if not profile.filing_status:
            missing.append("filing_status")
        if profile.dependents is None:
            missing.append("dependents")
        if not profile.employment_status:
            missing.append("employment_status")
        return missing

    def _suggest_profile_questions(self, current_profile: Optional[UserProfile]) -> List[str]:
        qs: List[str] = []
        if not current_profile:
            return [
                "What is your employment status (employed, self-employed, unemployed, retired, student)?",
                "What is your approximate annual income?",
                "What is your filing status (single, married joint, married separate, head of household)?",
                "Do you have any dependents? If yes, how many?"
            ]
        if not current_profile.employment_status:
            qs.append("What is your employment status (employed, self-employed, unemployed, retired, student)?")
        if not current_profile.annual_income and current_profile.annual_income != 0:
            qs.append("What is your approximate annual income?")
        if not current_profile.filing_status:
            qs.append("What is your filing status (single, married joint, married separate, head of household)?")
        if current_profile.dependents is None:
            qs.append("Do you have any dependents? If yes, how many?")
        return qs
