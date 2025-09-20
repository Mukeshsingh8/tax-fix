"""
Minimal expense extraction utility (stub version).
"""

from typing import Dict, Any
from datetime import datetime


def extract_expense_from_text(text: str) -> Dict[str, Any]:
    """
    Simple expense extraction from text.
    TODO: Move this logic directly into ActionAgent.
    """
    return {
        "description": "Expense",
        "amount": 0.0,
        "category": "other",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
