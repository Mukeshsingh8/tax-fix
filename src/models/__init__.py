"""Models package for TaxFix multi-agent system."""

from .user import User, UserProfile, TaxDocument
from .conversation import Conversation, Message, AgentResponse
from .tax_knowledge import TaxRule, Deduction, TaxCategory

__all__ = [
    "User",
    "UserProfile", 
    "TaxDocument",
    "Conversation",
    "Message",
    "AgentResponse",
    "TaxRule",
    "Deduction",
    "TaxCategory"
]
