"""Action-oriented agent for expense management and interactive suggestions."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.state import Message, AgentResponse, AgentType
from ..utils import format_currency, safe_agent_method
from .base import BaseAgent
from ..tools.expense_manager import ExpenseManager
from ..services.action_decisions import ActionDecisionMaker


class ActionAgent(BaseAgent):
    """Agent that handles action-oriented interactions like expense management."""

    def __init__(self, *args, **kwargs):
        """Initialize action agent."""
        super().__init__(AgentType.ACTION, *args, **kwargs)
        self.expense_manager = ExpenseManager(
            self.database_service, self.memory_service, self
        )
        self.decision_maker = ActionDecisionMaker(self.llm_service, self)

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

    @safe_agent_method(
        fallback_content="I can help with expense tracking and tax management. What would you like to do?",
        fallback_confidence=0.5
    )
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process message using LLM-driven decision making."""
        user_id = context.get("user_id")
        if not user_id:
            return await self.create_response(
                content="I need to know who you are to help with expense management.",
                confidence=0.0,
            )

        # Get decision from decision maker
        decision = await self.decision_maker.decide_action_json(message, context, user_profile)

        # Execute the decided action
        return await self._execute_action(decision, message, user_id, context)

    async def _execute_action(
        self,
        decision: Dict[str, Any],
        message: Message,
        user_id: str,
        context: Dict[str, Any],
    ) -> AgentResponse:
        """Execute the decided action."""
        action = decision.get("action", "general_guidance")
        expense_data = decision.get("expense_data")
        confidence = float(decision.get("confidence", 0.6))

        try:
            if action == "add_expense":
                return await self._handle_add_expense(expense_data, user_id, context, message)
            
            elif action == "suggest_expense":
                return await self._handle_suggest_expense(expense_data, context, confidence, message)
            
            elif action == "update_expense":
                return await self.expense_manager.update_expense(expense_data or {}, user_id, context)
            
            elif action == "delete_expense":
                expense_id = self._extract_expense_id(message.content, expense_data)
                return await self.expense_manager.delete_expense(expense_id, user_id, context)
            
            elif action == "read_expenses":
                return await self.expense_manager.read_expenses(user_id, context)
            
            else:  # general_guidance
                return await self._handle_general_guidance(message, context, decision.get("reasoning", ""))

        except Exception as e:
            self.logger.error(f"Action execution error: {e}")
            return await self.create_response(
                content="I encountered an error while processing your request. Please try again.",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
            )

    async def _handle_add_expense(
        self,
        expense_data: Optional[Dict[str, Any]],
        user_id: str,
        context: Dict[str, Any],
        message: Message
    ) -> AgentResponse:
        """Handle adding an expense."""
        # Check for existing pending expense first
        if not expense_data:
            expense_data = await self.expense_manager.get_pending_expense(context.get("session_id"))
        
        # If still no data, try to extract from message
        if not expense_data:
            from ..utils import extract_expense_from_text
            expense_data = extract_expense_from_text(message.content)
        
        # Validate we have enough data
        if not expense_data or expense_data.get("amount", 0) <= 0:
            return await self.create_response(
                content="I need the expense details (description and amount). Please share them and I'll add it.",
                confidence=0.4,
                reasoning="Missing expense details for addition",
            )

        # Add the expense
        result = await self.expense_manager.add_expense_directly(expense_data, user_id, context)
        
        # Clear pending expense on success
        if result.confidence > 0.8:
            await self.expense_manager.clear_pending_expense(context.get("session_id"))
        
        return result

    async def _handle_suggest_expense(
        self,
        expense_data: Optional[Dict[str, Any]],
        context: Dict[str, Any],
        confidence: float,
        message: Message
    ) -> AgentResponse:
        """Handle suggesting an expense for confirmation."""
        if not expense_data:
            from ..utils import extract_expense_from_text
            expense_data = extract_expense_from_text(message.content)
        
        return await self.expense_manager.suggest_expense(
            expense_data or {}, context, confidence
        )

    async def _handle_general_guidance(
        self,
        message: Message,
        context: Dict[str, Any],
        reasoning: str
    ) -> AgentResponse:
        """Handle general guidance requests."""
        try:
            # Determine guidance type based on message content
            guidance_type = self._determine_guidance_type(message.content)
            
            # Generate guidance content
            content = await self.decision_maker.create_guidance_response(
                message, context, guidance_type
            )
            
            # Get appropriate suggested actions
            suggested_actions = self.decision_maker.get_suggested_actions("general_guidance")
            metadata = self.decision_maker.create_guidance_metadata("general_guidance", guidance_type)
            
            return await self.create_response(
                content=content,
                reasoning=f"General guidance provided: {reasoning}",
                confidence=0.7,
                suggested_actions=suggested_actions,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"General guidance error: {e}")
            return await self.create_response(
                content="I can help you track expenses and manage your tax deductions. What would you like to do?",
                confidence=0.5,
                reasoning="Fallback guidance"
            )

    def _determine_guidance_type(self, content: str) -> str:
        """Determine the type of guidance needed."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["how", "what", "explain"]):
            return "clarification"
        elif any(word in content_lower for word in ["should", "recommend", "best"]):
            return "actionable"
        else:
            return "general"

    def _extract_expense_id(self, content: str, expense_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract expense ID from content or expense data."""
        if expense_data and "expense_id" in expense_data:
            return expense_data["expense_id"]
        
        # Try to extract from content (basic implementation)
        import re
        id_match = re.search(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', content)
        if id_match:
            return id_match.group(0)
        
        return None

    # Convenience methods for external access
    async def get_pending_expense(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get pending expense from manager."""
        return await self.expense_manager.get_pending_expense(session_id)

    async def clear_pending_expense(self, session_id: Optional[str]) -> None:
        """Clear pending expense via manager."""
        await self.expense_manager.clear_pending_expense(session_id)
