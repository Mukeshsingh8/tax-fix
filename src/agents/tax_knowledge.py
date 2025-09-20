"""Tax knowledge agent for providing tax guidance and calculations."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.state import Message, AgentResponse, AgentType
from ..models.user import UserProfile as DBUserProfile  # for typing clarity
from ..services.tax_knowledge_service import TaxKnowledgeService
from ..utils import to_dict, val_to_str
from .base import BaseAgent


class TaxKnowledgeAgent(BaseAgent):
    """Provides German tax guidance, deduction ideas, and quick calculations."""

    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.TAX_KNOWLEDGE, *args, **kwargs)
        self.tax_service = TaxKnowledgeService()

    async def get_system_prompt(self) -> str:
        return """
        You are the Tax Knowledge Agent for a German tax assistant.

        Your goals:
        - Give accurate, up-to-date German tax info (focus on 2024 figures).
        - Be concise (2–4 sentences), actionable, and in English.
        - Use German tax terminology with brief English explanations where helpful.
        - If calculation is needed and possible with known profile data, do it.
        - Don’t suggest consulting tax professionals.

        Style:
        - Direct, clear, specific. Use € amounts when applicable.
        - Mention relevant rules (e.g., Grundfreibetrag, Werbungskosten).
        - When data is missing for a calculation, ask 2–3 smart questions.
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
            # Load profile (fresh) for personalization
            user_id = context.get("user_id")
            db_profile: Optional[DBUserProfile] = (
                await self.database_service.get_user_profile(user_id) if user_id else None
            )

            # 1) Check if we’re missing critical info for what the user is asking
            missing_info = await self._detect_missing_information(message, db_profile, context)
            if missing_info:
                return await self._ask_clarifying_questions(missing_info, message, context)

            # 2) Retrieve relevant rules/deductions from the knowledge service
            relevant_rules = self.tax_service.search_tax_rules(message.content) or []
            relevant_deductions = self.tax_service.search_deductions(message.content) or []

            # 3) Generate concise guidance paragraph (context-aware)
            guidance = await self._generate_tax_guidance(
                message=message,
                relevant_rules=relevant_rules,
                relevant_deductions=relevant_deductions,
                user_profile=db_profile,
                context=context,
            )

            # 4) Rank/trim deductions for this user
            top_deductions = await self._identify_relevant_deductions(
                message=message,
                user_profile=db_profile,
                relevant_content={"deductions": [to_dict(d) for d in relevant_deductions]},
            )

            # 5) Perform calculation if the user is asking for one and we have enough data
            calculations = await self._perform_calculations(
                message=message, user_profile=db_profile, context=context
            )

            # 6) Compose final response parts
            response_content = await self._create_guidance_response(
                guidance=guidance,
                deductions=top_deductions,
                calculations=calculations,
                user_profile=db_profile,
            )

            return await self.create_response(
                content=response_content,
                reasoning="Provided German tax guidance with relevant rules, deductions, and optional calculation.",
                confidence=0.88,
                suggested_actions=[
                    {"action": "review_deductions", "description": "Review suggested deductions"},
                    {"action": "calculate_taxes", "description": "Run a full tax estimate"},
                    {"action": "track_expense", "description": "Add a work expense to track"}
                ],
                metadata={
                    "agent_type": "tax_knowledge",
                    "tax_topics": self._extract_tax_topics(message.content),
                    "relevant_deductions": top_deductions,
                    "calculations": calculations,
                },
            )

        except Exception as e:
            self.logger.error(f"TaxKnowledgeAgent.process error: {e}")
            return await self.create_response(
                content="Sorry, I hit a snag while generating tax guidance. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                metadata={"agent_type": "tax_knowledge", "error": str(e)}
            )

    # -----------------------------
    # Guidance generation
    # -----------------------------
    async def _generate_tax_guidance(
        self,
        message: Message,
        relevant_rules: List[Any],
        relevant_deductions: List[Any],
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any],
    ) -> str:
        try:
            # Compact, human-readable list to prime the model
            def format_rules(rules: List[Any]) -> List[str]:
                out = []
                for r in rules[:3]:
                    rd = to_dict(r)
                    title = rd.get("title") or rd.get("name") or "Tax Rule"
                    desc = rd.get("description") or ""
                    ex = rd.get("examples") or []
                    line = f"- {title}: {desc}"
                    if ex:
                        line += f" (e.g., {', '.join(ex[:3])})"
                    out.append(line)
                return out

            def format_deds(deds: List[Any]) -> List[str]:
                out = []
                for d in deds[:3]:
                    dd = to_dict(d)
                    name = dd.get("name") or "Deduction"
                    desc = dd.get("description") or ""
                    mx = dd.get("max_amount")
                    line = f"- {name}: {desc}"
                    if mx:
                        try:
                            line += f" (max €{float(mx):,.2f})"
                        except Exception:
                            pass
                    out.append(line)
                return out

            history = context.get("conversation_history") or []
            tail = history[-8:]
            hist_text = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in tail]) or "n/a"

            profile_blob = self._profile_snapshot(user_profile)

            prompt = f"""
You are a German tax expert. Provide a concise, actionable answer (2–4 sentences) to the user's question,
using the factual snippets below when relevant.

User question: "{message.content}"

User profile (for context):
{profile_blob}

Recent conversation (most recent first):
{hist_text}

Relevant tax rules (if any):
{chr(10).join(format_rules(relevant_rules)) or "- (none found)"}

Relevant deductions (if any):
{chr(10).join(format_deds(relevant_deductions)) or "- (none found)"}

Requirements:
- Keep it in English, but use German tax terms with brief clarity (e.g., Grundfreibetrag – basic allowance).
- Prefer concrete euro amounts if present above.
- Do not suggest consulting a tax professional.
- Keep it focused and actionable.
""".strip()

            return await self.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=False,
                system_prompt="Write 2–4 crisp sentences. Be accurate, specific, and helpful."
            )
        except Exception as e:
            self.logger.error(f"_generate_tax_guidance error: {e}")
            return "Here’s a quick overview based on German 2024 rules. I can also run a calculation if you share a bit more detail."

    # -----------------------------
    # Deductions
    # -----------------------------
    async def _identify_relevant_deductions(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        relevant_content: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        try:
            msg = (message.content or "").lower()
            deds = relevant_content.get("deductions", []) or []

            scored: List[Dict[str, Any]] = []
            for d in deds:
                name = (d.get("name") or "").lower()
                desc = (d.get("description") or "").lower()
                category = (d.get("category") or "").lower()

                # Simple relevance signals
                score = 0.0
                if any(tok in msg for tok in name.split() if tok):
                    score += 0.3
                if any(tok in msg for tok in desc.split()[:6]):
                    score += 0.2
                if user_profile:
                    # Profile-aligned boosts
                    emp = val_to_str(user_profile.employment_status)
                    if emp == "self_employed" and ("business" in name or "betrieb" in desc):
                        score += 0.25
                    if (user_profile.dependents or 0) > 0 and ("child" in name or "kinder" in desc):
                        score += 0.2
                    inc = float(user_profile.annual_income or 0.0)
                    if inc > 75000 and ("donation" in name or "spende" in desc or "charitable" in desc):
                        score += 0.1
                scored.append({
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "max_amount": d.get("max_amount"),
                    "category": category,
                    "relevance_score": round(min(1.0, score), 3),
                })

            scored.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored[:5]
        except Exception as e:
            self.logger.error(f"_identify_relevant_deductions error: {e}")
            return []

    # -----------------------------
    # Calculations
    # -----------------------------
    async def _perform_calculations(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            # Ask the LLM (structured) whether a calculation is being requested
            should_calc = await self._should_perform_calculation(message, user_profile)
            if not should_calc:
                return {}

            if not user_profile:
                return {}

            income = float(user_profile.annual_income or 0.0)
            filing_status = val_to_str(user_profile.filing_status) or "single"
            dependents = int(user_profile.dependents or 0)

            if income <= 0:
                return {}

            health_insurance_type = getattr(user_profile, "health_insurance_type", "statutory") or "statutory"
            age = int(getattr(user_profile, "age", 30) or 30)
            has_children = dependents > 0

            calculations = self.tax_service.calculate_german_tax(
                income=income,
                filing_status=filing_status,
                dependents=dependents,
                health_insurance_type=health_insurance_type,
                age=age,
                has_children=has_children,
            ) or {}

            # Optional: potential savings from typical deductions (service-specific)
            try:
                rel_deds = self.tax_service.get_relevant_deductions(self._profile_as_dict(user_profile))
                if rel_deds:
                    savings = self.tax_service.calculate_deduction_savings(income, rel_deds)
                    if savings:
                        calculations["deduction_savings"] = savings
            except Exception:
                pass

            return calculations
        except Exception as e:
            self.logger.error(f"_perform_calculations error: {e}")
            return {}

    async def _should_perform_calculation(
        self, message: Message, user_profile: Optional[DBUserProfile]
    ) -> bool:
        try:
            instruction = f"""
Determine if the user is asking for a numeric tax calculation or breakdown.

User Message: "{message.content}"

Return strictly this JSON object only:
{{"calc": true}}  if the user wants a tax amount, tax liability, net income, or a breakdown.
{{"calc": false}} otherwise.

No prose, no code fences.
""".strip()

            messages = [
                {"role": "system", "content": "Return compact JSON only."},
                {"role": "user", "content": instruction},
            ]
            result = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )
            return bool(result and isinstance(result, dict) and result.get("calc") is True)
        except Exception as e:
            self.logger.warning(f"_should_perform_calculation fallback due to error: {e}")
            text = (message.content or "").lower()
            return any(k in text for k in ["calculate", "how much", "liability", "net income", "estimate", "breakdown"])

    # -----------------------------
    # Missing info → questions
    # -----------------------------
    async def _detect_missing_information(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        try:
            instruction = f"""
Analyze the question and profile to decide what info is required for a complete answer.

User Question: "{message.content}"
Profile: {self._profile_snapshot(user_profile)}

Return a single JSON object with these boolean keys:
{{
  "needs_income": true/false,
  "needs_filing_status": true/false,
  "needs_dependents": true/false,
  "needs_employment_status": true/false,
  "is_calculation_request": true/false
}}

No prose, no code fences.
""".strip()

            messages = [
                {"role": "system", "content": "Return JSON only that matches the keys listed."},
                {"role": "user", "content": instruction},
            ]
            analysis = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            ) or {}

            missing: List[Dict[str, Any]] = []

            def missing_field(field: str, reason: str, priority: str, ctx: str):
                missing.append({"field": field, "reason": reason, "priority": priority, "context": ctx})

            if analysis.get("needs_income") and not getattr(user_profile or object(), "annual_income", None):
                missing_field("annual_income", "Needed for tax calculation and rate application", "high", "tax_calculation")

            if analysis.get("needs_filing_status") and not self._val(getattr(user_profile or object(), "filing_status", None)):
                missing_field("filing_status", "Affects tax rates and allowances", "high", "tax_calculation")

            if analysis.get("needs_dependents") and getattr(user_profile or object(), "dependents", None) is None:
                missing_field("dependents", "Determines child allowances", "medium", "deduction_analysis")

            if analysis.get("needs_employment_status") and not self._val(getattr(user_profile or object(), "employment_status", None)):
                missing_field("employment_status", "Affects work expense deductions", "medium", "deduction_analysis")

            if analysis.get("is_calculation_request") and not user_profile:
                missing_field("basic_profile", "Basic profile needed for personalized calculation", "high", "tax_calculation")

            return missing
        except Exception as e:
            self.logger.error(f"_detect_missing_information error: {e}")
            return []

    async def _ask_clarifying_questions(
        self,
        missing_info: List[Dict[str, Any]],
        message: Message,
        context: Dict[str, Any],
    ) -> AgentResponse:
        try:
            # Sort by priority (high → medium → low)
            priority_rank = {"high": 2, "medium": 1, "low": 0}
            missing_info.sort(key=lambda x: priority_rank.get(x.get("priority", "low"), 0), reverse=True)

            instruction = f"""
Generate 2–3 natural, conversational questions to gather the missing information.

Question: "{message.content}"
Missing fields: {[i['field'] for i in missing_info]}
Context tags: {[i['context'] for i in missing_info]}

Guidelines:
- Be specific and short.
- Explain briefly why each piece of info helps.
- Use German tax context.

Return a JSON array of objects with at least: "question" (string) and "field" (string).
No prose, no code fences.
""".strip()

            messages = [
                {"role": "system", "content": "Return only a JSON array as specified."},
                {"role": "user", "content": instruction},
            ]
            questions = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )
            if not isinstance(questions, list) or not questions:
                questions = self._generate_fallback_questions(missing_info)

            content = self._format_clarifying_response(questions, message, context)
            return await self.create_response(
                content=content,
                reasoning=f"Missing info: {[i['field'] for i in missing_info]}",
                confidence=0.82,
                suggested_actions=[
                    {"action": "provide_information", "description": "Answer these quick questions", "questions": questions},
                    {"action": "skip_profile", "description": "Continue with general guidance"}
                ],
                metadata={
                    "agent_type": "tax_knowledge",
                    "user_intent": "clarifying_questions",
                    "missing_fields": [i["field"] for i in missing_info],
                    "requires_followup": True,
                },
            )
        except Exception as e:
            self.logger.error(f"_ask_clarifying_questions error: {e}")
            return await self.create_response(
                content="To personalize this, could you share your annual income and filing status?",
                confidence=0.7,
                reasoning="Fallback clarifying question due to error",
                metadata={"agent_type": "tax_knowledge", "requires_followup": True},
            )

    def _generate_fallback_questions(self, missing_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        q: List[Dict[str, Any]] = []
        for info in missing_info:
            f = info["field"]
            if f == "annual_income":
                q.append({
                    "question": "What is your approximate annual income (gross)? This lets me calculate accurate tax and social contributions.",
                    "field": "annual_income",
                    "reason": "needed for calculation",
                    "priority": "high",
                })
            elif f == "filing_status":
                q.append({
                    "question": "What is your filing status (single, married joint, married separate, head of household)?",
                    "field": "filing_status",
                    "reason": "affects tax rates and allowances",
                    "priority": "high",
                })
            elif f == "dependents":
                q.append({
                    "question": "Do you have any dependents? If yes, how many?",
                    "field": "dependents",
                    "reason": "affects child allowances",
                    "priority": "medium",
                })
            elif f == "employment_status":
                q.append({
                    "question": "What is your employment status (employed, self-employed, unemployed, retired, student)?",
                    "field": "employment_status",
                    "reason": "affects work expense deductions",
                    "priority": "medium",
                })
        return q[:3]

    def _format_clarifying_response(
        self, questions: List[Dict[str, Any]], message: Message, context: Dict[str, Any]
    ) -> str:
        if not questions:
            return "To tailor this properly, please share your annual income and filing status."
        lines = [
            "I can tailor this precisely. Could you share a bit more:",
        ]
        for i, q in enumerate(questions, 1):
            lines.append(f"\n{i}. {q['question']}")
        lines.append(f"\nOnce I have this, I’ll answer: “{message.content}”.")
        return "".join(lines)

    # -----------------------------
    # Response composer
    # -----------------------------
    async def _create_guidance_response(
        self,
        guidance: str,
        deductions: List[Dict[str, Any]],
        calculations: Dict[str, Any],
        user_profile: Optional[DBUserProfile],
    ) -> str:
        from ..utils import (
            format_deductions_section,
            format_tax_calculation_section,
            format_insurance_details,
            format_deduction_savings,
        )
        
        parts: List[str] = []
        
        # Add main guidance text
        if guidance:
            parts.append(guidance.strip())

        # Add deductions section
        parts.extend(format_deductions_section(deductions))

        # Add tax calculations section
        parts.extend(format_tax_calculation_section(calculations))
        parts.extend(format_insurance_details(calculations))
        parts.extend(format_deduction_savings(calculations))

        # Add footer note
        parts.append(
            "\n*Figures reflect 2024 German rules (income tax and social security). "
            "You can boost savings by claiming eligible Werbungskosten (work expenses) "
            "and Sonderausgaben (special expenses).*"
        )
        
        return "\n".join(parts)

    # -----------------------------
    # Utilities
    # -----------------------------
    def _extract_tax_topics(self, content: str) -> List[str]:
        """Very light keyword tagging (German context)."""
        keywords = [
            # general
            "deduction", "absetzen", "werbungskosten", "sonderausgaben", "kinderfreibetrag",
            "riester", "kirchensteuer", "soli", "solidarity surcharge", "grundfreibetrag",
            "home office", "arbeitszimmer", "pendeln", "commute",
            "health insurance", "krankenversicherung", "pflegeversicherung",
            "retirement", "rente", "investments", "kapitalerträge",
            "tax return", "steuererklärung", "taxable income", "steuerpflichtiges einkommen",
            "allowance", "freibetrag",
        ]
        text = (content or "").lower()
        return sorted({k for k in keywords if k in text})

    def _profile_snapshot(self, profile: Optional[DBUserProfile]) -> str:
        if not profile:
            return "No profile on file."
        inc = f"€{float(profile.annual_income or 0):,.2f}"
        fil = val_to_str(profile.filing_status) or "single"
        dep = int(profile.dependents or 0)
        emp = val_to_str(profile.employment_status) or "unspecified"
        last = profile.last_interaction.strftime("%Y-%m-%d") if profile.last_interaction else "never"
        return (
            f"- Employment: {emp}\n"
            f"- Filing status: {fil}\n"
            f"- Annual income: {inc}\n"
            f"- Dependents: {dep}\n"
            f"- Last updated: {last}"
        )

    def _profile_as_dict(self, profile: Optional[DBUserProfile]) -> Dict[str, Any]:
        if not profile:
            return {}
        try:
            # Pydantic models have dict()
            return profile.dict()
        except Exception:
            # Fallback: attribute mapping
            return {
                "employment_status": val_to_str(getattr(profile, "employment_status", None)),
                "filing_status": val_to_str(getattr(profile, "filing_status", None)),
                "annual_income": float(getattr(profile, "annual_income", 0) or 0),
                "dependents": int(getattr(profile, "dependents", 0) or 0),
            }

