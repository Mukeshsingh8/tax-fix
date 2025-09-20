"""
Expense management logic extracted from ActionAgent.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from ..core.state import Message, AgentResponse
from .expense_tools import ExpenseTools
from ..utils import format_currency
from ..core.logging import get_logger

logger = get_logger(__name__)


class ExpenseManager:
    """Handles expense CRUD operations for the ActionAgent."""

    def __init__(self, database_service, memory_service, agent_instance):
        self.database_service = database_service
        self.memory_service = memory_service
        self.expense_tools = ExpenseTools(database_service)
        self.agent = agent_instance  # Reference to parent agent for create_response

    async def add_expense_directly(
        self,
        expense_data: Dict[str, Any],
        user_id: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Add an expense directly to the database."""
        try:
            expense_result = await self.expense_tools.write_expense(
                user_id=user_id,
                expense_data=expense_data
            )

            if expense_result:
                amount_str = format_currency(expense_data.get("amount", 0))
                return await self.agent.create_response(
                    content=f"✅ Added {expense_data.get('description', 'expense')}: {amount_str}. "
                            f"This should help with your tax deductions!",
                    confidence=0.9,
                    reasoning="Successfully added expense",
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View all your expenses"},
                        {"action": "add_another", "description": "Add another expense"},
                    ],
                    metadata={"expense_id": expense_result.get("id") if expense_result else None, "action_taken": "add_expense"},
                )
            else:
                return await self.agent.create_response(
                    content="I couldn't add that expense. Please check the details and try again.",
                    confidence=0.2,
                    reasoning="Expense addition failed",
                )

        except Exception as e:
            logger.error(f"Add expense error: {e}")
            return await self.agent.create_response(
                content="Sorry, I had trouble adding that expense. Please try again.",
                confidence=0.0,
                reasoning=f"Error adding expense: {str(e)}",
            )

    async def suggest_expense(
        self,
        expense_data: Dict[str, Any],
        context: Dict[str, Any],
        confidence_hint: float = 0.7
    ) -> AgentResponse:
        """Suggest an expense for user confirmation."""
        try:
            description = expense_data.get("description", "expense")
            amount = expense_data.get("amount", 0)
            category = expense_data.get("category", "other")

            # Store as pending expense for confirmation
            session_id = context.get("session_id")
            if session_id:
                await self._set_pending_expense(session_id, expense_data)

            amount_str = format_currency(amount) if amount > 0 else "amount not specified"
            
            return await self.agent.create_response(
                content=f"I think you want to track: **{description}** ({amount_str}, category: {category}). "
                        f"Should I add this expense?",
                confidence=confidence_hint,
                reasoning="Suggested expense for confirmation",
                suggested_actions=[
                    {"action": "confirm_expense", "description": "Yes, add this expense"},
                    {"action": "modify_expense", "description": "Let me modify the details"},
                    {"action": "cancel_expense", "description": "Cancel this expense"},
                ],
                metadata={"pending_expense": expense_data, "awaiting_confirmation": True},
            )

        except Exception as e:
            logger.error(f"Suggest expense error: {e}")
            return await self.agent.create_response(
                content="I can help you track expenses. What expense would you like to add?",
                confidence=0.4,
                reasoning=f"Error suggesting expense: {str(e)}",
            )

    async def update_expense(
        self,
        update_data: Dict[str, Any],
        user_id: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Update an existing expense."""
        try:
            expense_id = update_data.get("expense_id")
            if not expense_id:
                return await self.agent.create_response(
                    content="I need to know which expense to update. Can you specify the expense?",
                    confidence=0.3,
                    reasoning="Missing expense ID for update",
                )

            # Prepare update fields
            updates = {}
            if "description" in update_data:
                updates["description"] = update_data["description"]
            if "amount" in update_data:
                updates["amount"] = float(update_data["amount"])
            if "category" in update_data:
                updates["category"] = update_data["category"]
            if "date" in update_data:
                updates["date"] = update_data["date"]

            if not updates:
                return await self.agent.create_response(
                    content="What would you like to update about this expense?",
                    confidence=0.3,
                    reasoning="No update fields specified",
                )

            # Perform update
            success = await self.expense_tools.update_expense(expense_id, user_id, updates)
            
            if success:
                update_desc = ", ".join([f"{k}: {v}" for k, v in updates.items()])
                return await self.agent.create_response(
                    content=f"✅ Updated expense: {update_desc}",
                    confidence=0.9,
                    reasoning="Successfully updated expense",
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View all expenses"},
                    ],
                    metadata={"expense_id": expense_id, "action_taken": "update_expense"},
                )
            else:
                return await self.agent.create_response(
                    content="I couldn't update that expense. Please check the details.",
                    confidence=0.2,
                    reasoning="Expense update failed",
                )

        except Exception as e:
            logger.error(f"Update expense error: {e}")
            return await self.agent.create_response(
                content="Sorry, I had trouble updating that expense.",
                confidence=0.0,
                reasoning=f"Error updating expense: {str(e)}",
            )

    async def delete_expense(
        self,
        expense_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Delete an expense."""
        try:
            if not expense_id:
                return await self.agent.create_response(
                    content="Which expense would you like to delete?",
                    confidence=0.3,
                    reasoning="Missing expense ID for deletion",
                )

            success = await self.expense_tools.delete_expense(expense_id, user_id)
            
            if success:
                return await self.agent.create_response(
                    content="✅ Deleted the expense.",
                    confidence=0.9,
                    reasoning="Successfully deleted expense",
                    suggested_actions=[
                        {"action": "view_expenses", "description": "View remaining expenses"},
                    ],
                    metadata={"expense_id": expense_id, "action_taken": "delete_expense"},
                )
            else:
                return await self.agent.create_response(
                    content="I couldn't find or delete that expense.",
                    confidence=0.2,
                    reasoning="Expense deletion failed",
                )

        except Exception as e:
            logger.error(f"Delete expense error: {e}")
            return await self.agent.create_response(
                content="Sorry, I had trouble deleting that expense.",
                confidence=0.0,
                reasoning=f"Error deleting expense: {str(e)}",
            )

    async def read_expenses(
        self,
        user_id: str,
        context: Dict[str, Any],
        limit: int = 10
    ) -> AgentResponse:
        """Read and display user's expenses."""
        try:
            all_expenses = await self.expense_tools.read_expenses(
                user_id=user_id,
                filters=None
            )
            
            # Sort by date (most recent first) and limit
            expenses = sorted(
                all_expenses, 
                key=lambda x: x.get('date_incurred', ''), 
                reverse=True
            )[:limit]

            if not expenses:
                return await self.agent.create_response(
                    content="You don't have any expenses tracked yet. Would you like to add one?",
                    confidence=0.8,
                    reasoning="No expenses found",
                    suggested_actions=[
                        {"action": "add_expense", "description": "Add your first expense"},
                    ],
                )

            # Format expenses for display
            total_amount = sum(exp.get("amount", 0) for exp in expenses)
            expense_lines = []
            
            for exp in expenses[:5]:  # Show top 5
                amount_str = format_currency(exp.get("amount", 0))
                date = exp.get("date", "")
                desc = exp.get("description", "Unknown")
                category = exp.get("category", "other")
                
                expense_lines.append(f"• {date}: {desc} - {amount_str} ({category})")

            expenses_text = "\n".join(expense_lines)
            total_str = format_currency(total_amount)
            
            content = f"**Your Recent Expenses:**\n{expenses_text}\n\n**Total: {total_str}**"
            
            if len(expenses) > 5:
                content += f"\n\n(Showing 5 of {len(expenses)} expenses)"

            return await self.agent.create_response(
                content=content,
                confidence=0.95,
                reasoning="Successfully retrieved expenses",
                suggested_actions=[
                    {"action": "add_expense", "description": "Add another expense"},
                    {"action": "categorize_expenses", "description": "Review expense categories"},
                ],
                metadata={
                    "expense_count": len(expenses),
                    "total_amount": total_amount,
                    "action_taken": "read_expenses",
                },
            )

        except Exception as e:
            logger.error(f"Read expenses error: {e}")
            return await self.agent.create_response(
                content="I had trouble retrieving your expenses. Please try again.",
                confidence=0.0,
                reasoning=f"Error reading expenses: {str(e)}",
            )

    # Pending expense helpers
    async def _set_pending_expense(self, session_id: str, expense: Dict[str, Any]) -> None:
        """Store pending expense in session context."""
        try:
            await self.memory_service.update_conversation_context(
                session_id, {"pending_expense": expense}
            )
        except Exception as e:
            logger.warning(f"Unable to store pending_expense: {e}")

    async def get_pending_expense(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Retrieve pending expense from session context."""
        if not session_id:
            return None
        try:
            ctx = await self.memory_service.get_conversation_context(session_id)
            return ctx.get("pending_expense")
        except Exception as e:
            logger.warning(f"Unable to retrieve pending_expense: {e}")
            return None

    async def clear_pending_expense(self, session_id: Optional[str]) -> None:
        """Clear pending expense from session context."""
        if not session_id:
            return
        try:
            await self.memory_service.update_conversation_context(
                session_id, {"pending_expense": None}
            )
        except Exception as e:
            logger.warning(f"Unable to clear pending_expense: {e}")
