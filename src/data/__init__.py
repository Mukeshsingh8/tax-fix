"""Data package for TaxFix multi-agent system."""

from .german_tax_data import (
    get_german_tax_rules,
    get_german_deductions,
    get_german_user_profiles,
    get_german_conversations
)

__all__ = [
    "get_german_tax_rules",
    "get_german_deductions", 
    "get_german_user_profiles",
    "get_german_conversations"
]
