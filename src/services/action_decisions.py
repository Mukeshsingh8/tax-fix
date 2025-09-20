"""
Action decision logic extracted from ActionAgent.
"""

import json
from typing import Dict, List, Optional, Any
from ..core.state import Message
from ..utils import extract_expense_from_text
from ..core.logging import get_logger

logger = get_logger(__name__)


class ActionDecisionMaker:
    """Handles decision-making logic for the ActionAgent."""

    def __init__(self, llm_service, agent_instance):
        self.llm_service = llm_service
        self.agent = agent_instance

    async def decide_action_json(
        self,
        message: Message,
        context: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Decide what action to take based on the user's message."""
        try:
            # Build decision prompt
            prompt = self._build_decision_prompt(message, context, user_profile)
            
            # Get LLM decision
            messages = [
                {"role": "system", "content": "You are an expense management assistant. Return JSON only."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )

            if response and isinstance(response, dict):
                # Validate and enhance the response
                return self._validate_and_enhance_decision(response, message)
            else:
                self.logger.warning("LLM returned invalid decision, using fallback")
                return self._fallback_decision(message)

        except Exception as e:
            self.logger.error(f"Decision making error: {e}")
            return self._fallback_decision(message)

    def _build_decision_prompt(
        self,
        message: Message,
        context: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """Build the decision prompt for the LLM."""
        user_msg = message.content.strip()
        
        # Build context about user
        profile_context = ""
        if user_profile:
            profile_context = f"User profile: {user_profile}"

        # Build conversation context
        conversation_history = context.get("conversation_history", [])
        recent_messages = conversation_history[-3:] if conversation_history else []
        history_context = ""
        if recent_messages:
            history_context = f"Recent conversation: {recent_messages}"

        return f"""
Analyze this user message and decide the best action for expense management.

User message: "{user_msg}"
{profile_context}
{history_context}

Return JSON with this exact structure:
{{
  "action": "add_expense" | "suggest_expense" | "update_expense" | "delete_expense" | "read_expenses" | "general_guidance",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "expense_data": {{
    "description": "string",
    "amount": number,
    "category": "string",
    "date": "YYYY-MM-DD"
  }} or null
}}

Action guidelines:
- "add_expense": User clearly wants to add an expense with all details
- "suggest_expense": User mentions an expense but details are unclear
- "update_expense": User wants to modify an existing expense
- "delete_expense": User wants to remove an expense
- "read_expenses": User wants to see their expenses
- "general_guidance": General tax/expense advice

Categories: office_equipment, software, travel, education, communication, vehicle, meals, home_office, other

Only extract expense_data if relevant to the action.
""".strip()

    def _validate_and_enhance_decision(
        self,
        decision: Dict[str, Any],
        message: Message
    ) -> Dict[str, Any]:
        """Validate and enhance the LLM decision."""
        try:
            # Ensure required fields
            action = decision.get("action", "general_guidance")
            confidence = float(decision.get("confidence", 0.5))
            reasoning = decision.get("reasoning", "LLM decision")
            expense_data = decision.get("expense_data")

            # Validate action type
            valid_actions = [
                "add_expense", "suggest_expense", "update_expense", 
                "delete_expense", "read_expenses", "general_guidance"
            ]
            if action not in valid_actions:
                action = "general_guidance"
                confidence = 0.4

            # Enhance expense data if missing but action requires it
            if action in ["add_expense", "suggest_expense"] and not expense_data:
                expense_data = extract_expense_from_text(message.content)
                if expense_data.get("amount", 0) == 0:
                    # If we can't extract good expense data, suggest instead of add
                    action = "suggest_expense"

            # Validate expense data structure
            if expense_data:
                expense_data = self._validate_expense_data(expense_data)

            return {
                "action": action,
                "confidence": max(0.0, min(1.0, confidence)),
                "reasoning": reasoning,
                "expense_data": expense_data
            }

        except Exception as e:
            self.logger.error(f"Decision validation error: {e}")
            return self._fallback_decision(message)

    def _validate_expense_data(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean expense data."""
        try:
            # Ensure required fields with defaults
            cleaned = {
                "description": str(expense_data.get("description", "")).strip() or "Expense",
                "amount": float(expense_data.get("amount", 0)),
                "category": str(expense_data.get("category", "other")).lower(),
                "date": expense_data.get("date", "")
            }

            # Validate category
            valid_categories = [
                "office_equipment", "software", "travel", "education", 
                "communication", "vehicle", "meals", "home_office", "other"
            ]
            if cleaned["category"] not in valid_categories:
                cleaned["category"] = "other"

            # Validate date format (basic check)
            date = cleaned["date"]
            if not date or len(date) != 10 or date.count("-") != 2:
                from datetime import datetime
                cleaned["date"] = datetime.now().strftime("%Y-%m-%d")

            return cleaned

        except Exception as e:
            self.logger.error(f"Expense data validation error: {e}")
            from datetime import datetime
            return {
                "description": "Expense",
                "amount": 0.0,
                "category": "other",
                "date": datetime.now().strftime("%Y-%m-%d")
            }

    def _fallback_decision(self, message: Message) -> Dict[str, Any]:
        """Create fallback decision when LLM fails."""
        try:
            text_lower = message.content.lower()
            
            # Simple keyword-based fallback
            if any(word in text_lower for word in ["add", "track", "record", "spent"]):
                expense_data = extract_expense_from_text(message.content)
                if expense_data.get("amount", 0) > 0:
                    return {
                        "action": "suggest_expense",
                        "expense_data": expense_data,
                        "reasoning": "Fallback: detected expense mention",
                        "confidence": 0.6
                    }
            
            elif any(word in text_lower for word in ["show", "list", "expenses", "spent"]):
                return {
                    "action": "read_expenses",
                    "expense_data": None,
                    "reasoning": "Fallback: expense listing request",
                    "confidence": 0.7
                }
            
            elif any(word in text_lower for word in ["update", "change", "modify"]):
                return {
                    "action": "update_expense",
                    "expense_data": None,
                    "reasoning": "Fallback: expense update request",
                    "confidence": 0.6
                }
            
            elif any(word in text_lower for word in ["delete", "remove", "cancel"]):
                return {
                    "action": "delete_expense",
                    "expense_data": None,
                    "reasoning": "Fallback: expense deletion request",
                    "confidence": 0.6
                }

            # Default to general guidance
            return {
                "action": "general_guidance",
                "expense_data": None,
                "reasoning": "Fallback: general query",
                "confidence": 0.5
            }

        except Exception as e:
            self.logger.error(f"Fallback decision error: {e}")
            return {
                "action": "general_guidance",
                "expense_data": None,
                "reasoning": "Error fallback",
                "confidence": 0.5
            }

    async def create_guidance_response(
        self,
        message: Message,
        context: Dict[str, Any],
        guidance_type: str = "general"
    ) -> str:
        """Create guidance response using LLM."""
        try:
            from ..utils import create_tax_guidance_prompt
            
            prompt = create_tax_guidance_prompt(message.content, guidance_type)
            
            return await self.agent.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=True,
            )

        except Exception as e:
            self.logger.error(f"Guidance response error: {e}")
            return "I can help you track expenses and manage your tax deductions. What would you like to do?"

    def get_suggested_actions(self, action_type: str) -> List[Dict[str, str]]:
        """Get suggested actions based on the action type."""
        action_suggestions = {
            "add_expense": [
                {"action": "add_another", "description": "Add another expense"},
                {"action": "view_expenses", "description": "View all expenses"},
                {"action": "categorize", "description": "Review expense categories"},
            ],
            "suggest_expense": [
                {"action": "confirm", "description": "Confirm this expense"},
                {"action": "modify", "description": "Modify the details"},
                {"action": "cancel", "description": "Cancel this expense"},
            ],
            "read_expenses": [
                {"action": "add_expense", "description": "Add a new expense"},
                {"action": "export", "description": "Export expenses"},
                {"action": "categorize", "description": "Review categories"},
            ],
            "general_guidance": [
                {"action": "track_expense", "description": "Start tracking expenses"},
                {"action": "learn_deductions", "description": "Learn about deductions"},
                {"action": "calculate_taxes", "description": "Calculate tax liability"},
            ],
        }
        
        return action_suggestions.get(action_type, action_suggestions["general_guidance"])

    def create_guidance_metadata(self, action_type: str, guidance_type: str = "general") -> Dict[str, Any]:
        """Create metadata for guidance responses."""
        return {
            "action_type": action_type,
            "guidance_type": guidance_type,
            "source": "action_agent",
            "category": "expense_management",
            "actionable": True,
        }
