"""Action-oriented agent for expense management and interactive suggestions."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from ..core.state import Message, AgentResponse, AgentType
from ..tools.expense_tools import ExpenseTools
from ..utils import format_currency
from .base import BaseAgent


class ActionAgent(BaseAgent):
    """Agent that handles action-oriented interactions like expense management."""

    def __init__(self, *args, **kwargs):
        """Initialize action agent."""
        super().__init__(AgentType.ACTION, *args, **kwargs)
        self.expense_tools = ExpenseTools(self.database_service)

    async def get_system_prompt(self) -> str:
        """Get system prompt for action agent."""
        return """
You are the Action Agent for the TaxFix system.

Your role is to:
1) Suggest concrete, actionable steps for expense tracking and tax management
2) Add / update / delete / show expenses
3) Ask for missing details only when strictly needed
4) Keep replies concise, clear, and engaging
5) Use German tax terms with brief English explanations (e.g., Werbungskosten = work expenses)
6) Provide users with their information (like all of their expense)

ALWAYS reply in English.
Focus on action, not long explanations.
"""

    # ---------------------------
    # Public entry
    # ---------------------------
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process message using LLM-driven decision making."""
        try:
            user_id = context.get("user_id")
            if not user_id:
                return await self.create_response(
                    content="I need to know who you are to help with expense management.",
                    confidence=0.0,
                )

            # Decide an action with structured JSON
            decision = await self._decide_action_json(message, context, user_profile)

            # Execute
            return await self._execute_action(decision, message, user_id, context)
        except Exception as e:
            self.logger.error(f"Error in action agent processing: {e}")
            return await self.create_response(
                content="I encountered an error while processing your request.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    # ---------------------------
    # Decision via structured JSON
    # ---------------------------
    async def _decide_action_json(
        self,
        message: Message,
        context: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Let the LLM pick an action using strict JSON (schema described in prompt)."""
        # Build compact history
        hist = ""
        history = context.get("conversation_history") or []
        if history:
            tail = history[-8:]
            hist = "\n".join([f"- {m.get('role','?')}: {(m.get('content') or '')[:250]}" for m in tail])

        schema_desc = """
Output a single JSON object with keys:
- action: one of ["add_expense","suggest_expense","update_expense","delete_expense","read_expenses","general_guidance","clarify_expense"]
- expense_data: null or an object with optional keys {id, description, amount, category, date, tax_year, deduction_type, status}
- reasoning: short string
- confidence: number 0..1

No commentary, no code fences, JSON only.
""".strip()

        prompt = f"""
You are deciding the next ACTION in an expense-tracking flow.

Message:
\"\"\"{message.content}\"\"\"

Recent conversation (last 8):
{hist or "n/a"}

User profile (summary):
{user_profile or {}}

POSSIBLE ACTIONS:
- add_expense: user explicitly asks to add or confirms adding
- suggest_expense: user mentions an expense or asks "can I claim...?"
- update_expense: change fields of an existing expense
- delete_expense: remove an expense
- read_expenses: show the user's expenses
- general_guidance: broad suggestions for deductible items and next steps
- clarify_expense: only for genuinely complex rule clarifications

Guidelines:
- If user says “yes / add it” after a suggestion, use add_expense (even if fields are missing: we'll pick up the pending item from context).
- If user mentions buying something for work or asks if deductible -> suggest_expense.
- Ask for missing details ONLY if necessary to perform the action.
- If the user is asking for thier information use read_expenses
- Keep reasons short.

{schema_desc}
""".strip()

        messages = [
            {"role": "system", "content": "Return strictly valid JSON as specified. No commentary."},
            {"role": "user", "content": prompt},
        ]
        try:
            data = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )
            # Normalize small glitches
            if not isinstance(data, dict):
                data = {}
            action = str(data.get("action", "general_guidance")).strip()
            expense_data = data.get("expense_data")
            if isinstance(expense_data, dict):
                if "amount" in expense_data and expense_data["amount"] in (None, ""):
                    expense_data["amount"] = 0
                if "date" in expense_data and expense_data["date"]:
                    expense_data["date"] = str(expense_data["date"]).strip()
            return {
                "action": action,
                "expense_data": expense_data,
                "reasoning": data.get("reasoning", ""),
                "confidence": float(data.get("confidence", 0.6)),
            }

        except Exception as e:
            self.logger.warning(f"Decision JSON failed, fallback: {e}")
            # Minimal fallback routing
            txt = message.content.lower()
            if any(w in txt for w in ["add it", "yes add", "please add"]):
                return {"action": "add_expense", "expense_data": None, "reasoning": "fallback yes/add", "confidence": 0.7}
            if any(w in txt for w in ["show my expenses", "view expenses", "list expenses"]):
                return {"action": "read_expenses", "expense_data": None, "reasoning": "fallback list", "confidence": 0.7}
            if any(w in txt for w in ["bought", "purchase", "can i claim", "deductible"]):
                return {"action": "suggest_expense", "expense_data": None, "reasoning": "fallback suggest", "confidence": 0.65}
            return {"action": "general_guidance", "expense_data": None, "reasoning": "fallback", "confidence": 0.5}

    # ---------------------------
    # Execute
    # ---------------------------
    async def _execute_action(
        self,
        decision: Dict[str, Any],
        message: Message,
        user_id: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        action = (decision or {}).get("action", "general_guidance")
        expense_data = (decision or {}).get("expense_data")
        confidence = float((decision or {}).get("confidence", 0.6))

        if action == "add_expense":
            # If LLM didn't provide details, try the pending one saved in context
            if not expense_data:
                expense_data = await self._get_pending_expense(context.get("session_id"))
            if not expense_data:
                # Heuristic extraction from the user message as a last resort
                expense_data = self._extract_minimal_expense_from_text(message.content)
            if expense_data:
                res = await self._add_expense_directly(expense_data, user_id, context)
                # clear pending once added successfully
                await self._clear_pending_expense(context.get("session_id"))
                return res
            return await self.create_response(
                content="I’m missing the expense details (description/amount/date). Please share them and I’ll add it.",
                confidence=0.4,
                reasoning="add_expense requested but missing fields",
            )

        if action == "suggest_expense":
            if not expense_data:
                # try to guess minimal skeleton so user can confirm quickly
                expense_data = self._extract_minimal_expense_from_text(message.content)
            return await self._suggest_expense(expense_data or {}, context, confidence_hint=confidence)

        if action == "update_expense":
            return await self._update_expense(expense_data or {}, user_id, context)

        if action == "delete_expense":
            return await self._delete_expense(expense_data or {}, user_id, context)

        if action == "read_expenses":
            return await self._read_expenses(user_id, context)

        if action == "clarify_expense":
            return await self._clarify_expense(message, context)

        # Fallback
        return await self._provide_general_guidance(message, context)

    # ---------------------------
    # Concrete ops
    # ---------------------------
    async def _add_expense_directly(
        self,
        expense_data: Dict[str, Any],
        user_id: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        try:
            # Normalize minimal fields
            expense = {
                "description": expense_data.get("description") or "Expense",
                "amount": float(expense_data.get("amount") or 0.0),
                "category": (expense_data.get("category") or "other").strip().lower().replace(" ", "_"),
                "date": expense_data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                "tax_year": int(expense_data.get("tax_year") or datetime.now().year),
                "deduction_type": expense_data.get("deduction_type") or "above_line",
                "status": expense_data.get("status") or "confirmed",
                "suggested_by_ai": bool(expense_data.get("suggested_by_ai", False)),
            }

            created = await self.expense_tools.write_expense(user_id=user_id, expense_data=expense)
            if created:
                return await self.create_response(
                    content=f"✅ Added expense: **{created.get('description')}** – {format_currency(created.get('amount'))} "
                            f"({created.get('category','other').replace('_',' ')}, {created.get('date_incurred')}).",
                    reasoning="Added via ExpenseTools.write_expense",
                    confidence=0.95,
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View all expenses"},
                        {"action": "add_more", "description": "Add another expense"},
                    ],
                    metadata={"expense_added": created},
                )
            return await self.create_response(
                content="I had trouble adding that expense. Please try again or provide more details.",
                reasoning="DB write returned None",
                confidence=0.3,
            )
        except Exception as e:
            self.logger.error(f"Error adding expense directly: {e}")
            return await self.create_response(
                content="I encountered an error while adding your expense. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    async def _suggest_expense(
        self,
        expense_data: Dict[str, Any],
        context: Dict[str, Any],
        confidence_hint: float = 0.8,
    ) -> AgentResponse:
        """Suggest expense and cache it for one-turn confirm (“yes, add it”)."""
        try:
            desc = (expense_data.get("description") or "this item").strip()
            amt = expense_data.get("amount")
            cat = (expense_data.get("category") or "other").replace("_", " ").title()

            needs_amount = amt in (None, 0)
            needs_desc = not desc or desc in {"laptop", "computer", "equipment", "item"}

            # Save as pending so the next "yes, add it" can work
            await self._set_pending_expense(context.get("session_id"), expense_data)

            if needs_amount or needs_desc:
                content = (
                    f"**Yes, you can usually claim {desc} as Werbungskosten (work expenses).**\n\n"
                    f"To add it, please confirm:\n"
                    f"1) **Amount** (e.g., 800)\n"
                    f"2) **Purchase date** (YYYY-MM-DD)\n"
                    f"3) **Mainly for work?** (Yes/No)\n\n"
                    f"Say **\"add it\"** after you confirm."
                )
            else:
                content = (
                    f"**Looks deductible:** {desc} – {format_currency(amt)} as {cat} (Werbungskosten).\n\n"
                    f"Would you like me to add this to your expense records now?\n"
                    f"Just say **\"yes\"** or **\"add it\"**."
                )

            return await self.create_response(
                content=content,
                reasoning="Suggested expense; cached as pending for quick confirm",
                confidence=max(0.75, confidence_hint),
                suggested_actions=[
                    {"action": "add_expense", "description": f"Add {desc}"},
                    {"action": "learn_more", "description": f"Learn about {cat} deductions"},
                    {"action": "skip", "description": "Skip this one"},
                ],
                metadata={"suggested_expense": expense_data, "needs_info": needs_amount or needs_desc},
            )
        except Exception as e:
            self.logger.error(f"Error suggesting expense: {e}")
            return await self.create_response(
                content="I can help you track expenses for your tax return. What would you like to add?",
                confidence=0.5,
                reasoning=f"Error: {str(e)}",
            )

    async def _update_expense(
        self,
        expense_data: Dict[str, Any],
        user_id: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        try:
            expense_id = expense_data.get("id")
            if not expense_id:
                return await self.create_response(
                    content="I need the expense ID (or tell me which one) to update.",
                    reasoning="Missing expense ID",
                    confidence=0.35,
                )

            updates = {k: v for k, v in expense_data.items() if k != "id"}
            updated = await self.expense_tools.update_expense(expense_id=expense_id, user_id=user_id, updates=updates)
            if updated:
                return await self.create_response(
                    content=f"✅ Updated: **{updated.get('description')}** – {format_currency(updated.get('amount'))}.",
                    reasoning="Updated via ExpenseTools.update_expense",
                    confidence=0.95,
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View all expenses"},
                        {"action": "update_more", "description": "Update another expense"},
                    ],
                    metadata={"expense_updated": updated},
                )
            return await self.create_response(
                content="I couldn't find that expense to update. Please check the ID or description.",
                reasoning="Expense not found",
                confidence=0.3,
            )
        except Exception as e:
            self.logger.error(f"Error updating expense: {e}")
            return await self.create_response(
                content="I encountered an error while updating your expense. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    async def _delete_expense(
        self,
        expense_data: Dict[str, Any],
        user_id: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        try:
            expense_id = expense_data.get("id")
            if not expense_id:
                return await self.create_response(
                    content="I need the expense ID to delete it.",
                    reasoning="Missing expense ID",
                    confidence=0.35,
                )

            deleted = await self.expense_tools.delete_expense(expense_id=expense_id, user_id=user_id)
            if deleted:
                return await self.create_response(
                    content="✅ Deleted that expense.",
                    reasoning="Deleted via ExpenseTools.delete_expense",
                    confidence=0.95,
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View remaining expenses"},
                        {"action": "add_expense", "description": "Add a new expense"},
                    ],
                    metadata={"expense_deleted": expense_id},
                )
            return await self.create_response(
                content="I couldn't find that expense to delete. Please check the ID.",
                reasoning="Expense not found",
                confidence=0.3,
            )
        except Exception as e:
            self.logger.error(f"Error deleting expense: {e}")
            return await self.create_response(
                content="I encountered an error while deleting your expense. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    async def _read_expenses(self, user_id: str, context: Dict[str, Any]) -> AgentResponse:
        try:
            expenses = await self.expense_tools.read_expenses(user_id)
            if not expenses:
                return await self.create_response(
                    content="You don’t have any expenses recorded yet. Want to add one?",
                    reasoning="No expenses found",
                    confidence=0.85,
                    suggested_actions=[
                        {"action": "add_expense", "description": "Add your first expense"},
                        {"action": "learn_deductions", "description": "Learn about tax deductions"},
                    ],
                )

            # Show first 10
            lines = []
            total = 0.0
            for e in expenses[:10]:
                amt = float(e.get("amount") or 0.0)
                total += amt
                lines.append(
                    f"• {e.get('description','Expense')} – {format_currency(amt)} "
                    f"({(e.get('category','other') or 'other').replace('_',' ')}, {e.get('date_incurred')})"
                )

            summary = await self.expense_tools.get_expense_summary(user_id)

            text = (
                f"**Your Expenses ({len(expenses)} total, {format_currency(total)}):**\n\n"
                + "\n".join(lines)
                + "\n\n**Summary:**\n"
                + f"• Total Amount: {format_currency(summary.get('total_amount', 0))}\n"
                + f"• Average Expense: {format_currency(summary.get('average_expense', 0))}\n"
                + f"• Categories: {', '.join(summary.get('category_breakdown', {}).keys()) or '—'}\n"
                + (f"\n*Showing first 10. You have {len(expenses)} total.*" if len(expenses) > 10 else "")
            )

            return await self.create_response(
                content=text,
                reasoning="Listed expenses and summary",
                confidence=0.95,
                suggested_actions=[
                    {"action": "add_expense", "description": "Add another expense"},
                    {"action": "update_expense", "description": "Update an expense"},
                    {"action": "delete_expense", "description": "Delete an expense"},
                ],
                metadata={"expenses_count": len(expenses), "total_amount": total},
            )
        except Exception as e:
            self.logger.error(f"Error reading expenses: {e}")
            return await self.create_response(
                content="I encountered an error while retrieving your expenses. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    async def _provide_general_guidance(self, message: Message, context: Dict[str, Any]) -> AgentResponse:
        try:
            prompt = f"""
Provide helpful, *action-oriented* German tax guidance for this user question:

User: "{message.content}"

Focus on:
1) Specific actions to take next
2) Common deductible items (Werbungskosten) relevant to the user
3) A short, clear next step

Keep it to 2–3 sentences. Always reply in English.
"""
            messages = [{"role": "user", "content": prompt}]
            content = await self.generate_llm_response(
                messages=messages,
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=True,
                system_prompt="You are a helpful German tax advisor focused on actionable advice.",
            )
            return await self.create_response(
                content=content,
                reasoning="General action-oriented guidance",
                confidence=0.7,
                suggested_actions=[
                    {"action": "track_expenses", "description": "Start tracking your expenses"},
                    {"action": "learn_deductions", "description": "Learn about tax deductions"},
                    {"action": "calculate_taxes", "description": "Calculate your tax liability"},
                ],
                metadata={"response_type": "general_guidance"},
            )
        except Exception as e:
            self.logger.error(f"Error providing general guidance: {e}")
            return await self.create_response(
                content="I can help with expense tracking and tax management. What would you like to do?",
                confidence=0.5,
                reasoning=f"Error: {str(e)}",
            )

    async def _clarify_expense(self, message: Message, context: Dict[str, Any]) -> AgentResponse:
        try:
            prompt = f"""
Provide clear clarification about German tax expenses for this question:

User: "{message.content}"

Cover:
- Deductibility criteria
- Amount limits/requirements
- A short, practical example

Be concise and accurate. Reply in English.
"""
            messages = [{"role": "user", "content": prompt}]
            content = await self.generate_llm_response(
                messages=messages,
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=True,
                system_prompt="You are a German tax expert providing clear, accurate clarifications.",
            )
            return await self.create_response(
                content=content,
                reasoning="Expense clarification",
                confidence=0.8,
                suggested_actions=[
                    {"action": "track_expense", "description": "Track this type of expense"},
                    {"action": "learn_more", "description": "Learn more about this category"},
                    {"action": "ask_question", "description": "Ask another question"},
                ],
                metadata={"response_type": "clarification"},
            )
        except Exception as e:
            self.logger.error(f"Error providing clarification: {e}")
            return await self.create_response(
                content="I can help clarify tax rules and expenses. What would you like to know more about?",
                confidence=0.5,
                reasoning=f"Error: {str(e)}",
            )

    # ---------------------------
    # Pending expense helpers (context storage)
    # ---------------------------
    async def _set_pending_expense(self, session_id: Optional[str], expense: Dict[str, Any]) -> None:
        if not session_id:
            return
        try:
            await self.memory_service.update_conversation_context(session_id, {"pending_expense": expense})
        except Exception as e:
            self.logger.warning(f"Unable to store pending_expense: {e}")

    async def _get_pending_expense(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        try:
            ctx = await self.memory_service.get_conversation_context(session_id) or {}
            return ctx.get("pending_expense")
        except Exception as e:
            self.logger.warning(f"Unable to retrieve pending_expense: {e}")
            return None

    async def _clear_pending_expense(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        try:
            await self.memory_service.update_conversation_context(session_id, {"pending_expense": None})
        except Exception as e:
            self.logger.warning(f"Unable to clear pending_expense: {e}")

    # ---------------------------
    # Heuristic extraction
    # ---------------------------
    def _extract_minimal_expense_from_text(self, text: str) -> Dict[str, Any]:
        """Very light heuristic to pull a description and amount from free text."""
        desc = "expense"
        # naive description pick: first noun-ish phrase
        m_desc = re.search(r"\b(bought|purchase|laptop|chair|desk|software|ticket|train|hotel|course)\b", text, re.I)
        if m_desc:
            word = m_desc.group(0)
            mapping = {"bought": "purchase", "purchase": "purchase"}
            desc = mapping.get(word.lower(), word.title())

        amt = 0.0
        m_amt = re.search(r"(\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,](\d{1,2}))?\s*(?:€|eur|euro)?", text, re.I)
        if m_amt:
            whole = m_amt.group(1).replace(".", "").replace(",", "")
            dec = m_amt.group(2) or ""
            try:
                amt = float(f"{whole}.{dec}" if dec else whole)
            except Exception:
                amt = 0.0

        return {
            "description": desc,
            "amount": amt,
            "category": "other",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }