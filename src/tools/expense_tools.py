"""Expense database tools for CRUD operations on expense table."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..services.database import DatabaseService
from ..core.logging import get_logger

logger = get_logger(__name__)


class ExpenseTools:
    """Tools for database operations on expense documents (document_type = 'tax_expense')."""

    def __init__(self, database_service: DatabaseService):
        self.database = database_service
        self.logger = get_logger(__name__)

    # ---------------------------
    # Read
    # ---------------------------
    async def read_expenses(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read expenses for a user with optional filters.

        filters supports (all optional):
          - category: str
          - year: int
          - status: str
          - date_from: ISO str
          - date_to: ISO str
        """
        try:
            docs = await self.database.get_user_tax_documents(user_id)
            expenses: List[Dict[str, Any]] = []

            # Convert and filter in Python (keeps DatabaseService API consistent)
            for doc in docs:
                if getattr(doc, "document_type", None) != "tax_expense":
                    continue

                exp = (doc.metadata or {}).get("expense_data", {})
                # normalize fields
                exp = {
                    "id": doc.id,
                    "user_id": doc.user_id,
                    "description": exp.get("description", doc.description or "Expense"),
                    "amount": float(exp.get("amount", doc.amount or 0.0) or 0.0),
                    "category": exp.get("category", (doc.metadata or {}).get("category", "other")),
                    "date_incurred": exp.get("date_incurred", exp.get("date", None)) or datetime.utcnow().strftime("%Y-%m-%d"),
                    "tax_year": int(exp.get("tax_year", getattr(doc, "year", datetime.utcnow().year))),
                    "status": exp.get("status", (doc.metadata or {}).get("status", "confirmed")),
                    "created_at": getattr(doc, "created_at", None) or datetime.utcnow().isoformat(),
                    "updated_at": getattr(doc, "updated_at", None) or datetime.utcnow().isoformat(),
                }

                # Apply filters
                if filters:
                    if "category" in filters and exp["category"] != filters["category"]:
                        continue
                    if "year" in filters and int(exp["tax_year"]) != int(filters["year"]):
                        continue
                    if "status" in filters and exp["status"] != filters["status"]:
                        continue
                    if "date_from" in filters:
                        try:
                            if exp["date_incurred"] < filters["date_from"]:
                                continue
                        except Exception:
                            pass
                    if "date_to" in filters:
                        try:
                            if exp["date_incurred"] > filters["date_to"]:
                                continue
                        except Exception:
                            pass

                expenses.append(exp)

            self.logger.info(f"Read {len(expenses)} expenses for user {user_id}")
            return expenses
        except Exception as e:
            self.logger.error(f"Error reading expenses: {e}")
            return []

    # ---------------------------
    # Create
    # ---------------------------
    async def write_expense(self, user_id: str, expense_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new expense document (document_type='tax_expense').
        """
        try:
            expense_id = f"exp_{int(datetime.utcnow().timestamp() * 1000)}"

            # Normalize payload
            expense = {
                "id": expense_id,
                "user_id": user_id,
                "description": expense_data.get("description", "Expense"),
                "amount": float(expense_data.get("amount", 0.0) or 0.0),
                "category": (expense_data.get("category") or "other"),
                "date_incurred": expense_data.get("date") or expense_data.get("date_incurred") or datetime.utcnow().strftime("%Y-%m-%d"),
                "tax_year": int(expense_data.get("tax_year", datetime.utcnow().year)),
                "deduction_type": expense_data.get("deduction_type", "above_line"),
                "status": expense_data.get("status", "confirmed"),
                "suggested_by_ai": bool(expense_data.get("suggested_by_ai", False)),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Build tax document model
            from ..models.user import TaxDocument

            document = TaxDocument(
                id=expense["id"],
                user_id=expense["user_id"],
                document_type="tax_expense",
                year=expense["tax_year"],
                amount=expense["amount"],
                description=expense["description"],
                metadata={
                    "expense_data": expense,
                    "category": expense["category"],
                    "status": expense["status"],
                },
            )

            await self.database.create_tax_document(document)
            self.logger.info(f"Created expense: {expense['id']} - {expense['description']} - €{expense['amount']}")
            return expense
        except Exception as e:
            self.logger.error(f"Error writing expense: {e}")
            return None

    # ---------------------------
    # Update
    # ---------------------------
    async def update_expense(self, expense_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing expense document."""
        try:
            docs = await self.database.get_user_tax_documents(user_id)
            target = None
            for d in docs:
                if d.id == expense_id and d.document_type == "tax_expense":
                    target = d
                    break
            if not target:
                self.logger.error(f"Expense {expense_id} not found for user {user_id}")
                return None

            current = (target.metadata or {}).get("expense_data", {})

            # Allowed updates
            allowed = {
                "description",
                "amount",
                "category",
                "date_incurred",
                "date",
                "status",
                "deduction_type",
                "tax_year",
            }
            for k, v in list(updates.items()):
                if k not in allowed:
                    updates.pop(k, None)

            # Coerce and normalize
            new_exp = current.copy()
            if "date" in updates and updates.get("date") and not updates.get("date_incurred"):
                updates["date_incurred"] = updates["date"]
            if "amount" in updates and updates["amount"] is not None:
                try:
                    updates["amount"] = float(updates["amount"])
                except Exception:
                    updates["amount"] = current.get("amount", 0.0)

            new_exp.update(updates)
            new_exp["updated_at"] = datetime.utcnow().isoformat()
            if "tax_year" in new_exp:
                try:
                    new_exp["tax_year"] = int(new_exp["tax_year"])
                except Exception:
                    new_exp["tax_year"] = current.get("tax_year", datetime.utcnow().year)

            # Reflect into document
            target.metadata = target.metadata or {}
            target.metadata["expense_data"] = new_exp
            target.metadata["category"] = new_exp.get("category", "other")
            target.metadata["status"] = new_exp.get("status", "confirmed")
            target.amount = float(new_exp.get("amount", target.amount or 0.0))
            target.description = new_exp.get("description", target.description or "Expense")
            if hasattr(target, "year"):
                target.year = int(new_exp.get("tax_year", getattr(target, "year", datetime.utcnow().year)))

            await self.database.update_tax_document(target)
            self.logger.info(f"Updated expense: {expense_id} with updates: {updates}")
            return new_exp
        except Exception as e:
            self.logger.error(f"Error updating expense: {e}")
            return None

    # ---------------------------
    # Delete
    # ---------------------------
    async def delete_expense(self, expense_id: str, user_id: str) -> bool:
        """Delete an expense document."""
        try:
            docs = await self.database.get_user_tax_documents(user_id)
            target = None
            for d in docs:
                if d.id == expense_id and d.document_type == "tax_expense":
                    target = d
                    break
            if not target:
                self.logger.error(f"Expense {expense_id} not found for user {user_id}")
                return False

            await self.database.delete_tax_document(expense_id)
            self.logger.info(f"Deleted expense: {expense_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting expense: {e}")
            return False

    # ---------------------------
    # Read single
    # ---------------------------
    async def get_expense_by_id(self, expense_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific expense by ID."""
        try:
            docs = await self.database.get_user_tax_documents(user_id)
            for d in docs:
                if d.id == expense_id and d.document_type == "tax_expense":
                    exp = (d.metadata or {}).get("expense_data", {})
                    return {
                        "id": d.id,
                        "user_id": d.user_id,
                        "description": exp.get("description", d.description or "Expense"),
                        "amount": float(exp.get("amount", d.amount or 0.0) or 0.0),
                        "category": exp.get("category", (d.metadata or {}).get("category", "other")),
                        "date_incurred": exp.get("date_incurred", exp.get("date", None)) or datetime.utcnow().strftime("%Y-%m-%d"),
                        "tax_year": int(exp.get("tax_year", getattr(d, "year", datetime.utcnow().year))),
                        "status": exp.get("status", (d.metadata or {}).get("status", "confirmed")),
                        "created_at": getattr(d, "created_at", None) or datetime.utcnow().isoformat(),
                        "updated_at": getattr(d, "updated_at", None) or datetime.utcnow().isoformat(),
                    }
            return None
        except Exception as e:
            self.logger.error(f"Error getting expense by ID: {e}")
            return None

    # ---------------------------
    # Summary
    # ---------------------------
    async def get_expense_summary(self, user_id: str, tax_year: Optional[int] = None) -> Dict[str, Any]:
        """Aggregate totals, categories, and monthly breakdown."""
        try:
            filters = {"year": tax_year} if tax_year else None
            expenses = await self.read_expenses(user_id, filters)

            if not expenses:
                return {
                    "total_expenses": 0,
                    "total_amount": 0.0,
                    "category_breakdown": {},
                    "monthly_breakdown": {},
                    "average_expense": 0.0,
                }

            total_amount = sum(float(e.get("amount") or 0.0) for e in expenses)
            category_breakdown: Dict[str, float] = {}
            monthly_breakdown: Dict[str, float] = {}

            for e in expenses:
                cat = e.get("category", "other")
                category_breakdown[cat] = category_breakdown.get(cat, 0.0) + float(e.get("amount") or 0.0)

                ds = e.get("date_incurred")
                month = None
                if ds:
                    try:
                        # YYYY-MM or YYYY-MM-DD → YYYY-MM
                        month = ds[:7]
                    except Exception:
                        month = None
                if month:
                    monthly_breakdown[month] = monthly_breakdown.get(month, 0.0) + float(e.get("amount") or 0.0)

            return {
                "total_expenses": len(expenses),
                "total_amount": total_amount,
                "category_breakdown": category_breakdown,
                "monthly_breakdown": monthly_breakdown,
                "average_expense": total_amount / len(expenses) if expenses else 0.0,
            }
        except Exception as e:
            self.logger.error(f"Error generating expense summary: {e}")
            return {
                "total_expenses": 0,
                "total_amount": 0.0,
                "category_breakdown": {},
                "monthly_breakdown": {},
                "average_expense": 0.0,
            }
