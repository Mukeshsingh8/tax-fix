"""
Minimal guidance generation utility (stub version).
"""

from typing import Dict, Any, List


def create_tax_guidance_prompt(user_message: str, guidance_type: str = "general") -> str:
    """
    Simple tax guidance prompt.
    TODO: Move this logic directly into ActionAgent.
    """
    return f"Answer this German tax question: {user_message}"


def create_suggested_actions(guidance_type: str) -> List[Dict[str, str]]:
    """
    Simple suggested actions.
    TODO: Move this logic directly into ActionAgent.
    """
    return [
        {"action": "track_expenses", "description": "Start tracking your expenses"},
        {"action": "ask_question", "description": "Ask another question"},
    ]


def create_guidance_metadata(guidance_type: str) -> Dict[str, Any]:
    """
    Simple guidance metadata.
    TODO: Move this logic directly into ActionAgent.
    """
    return {
        "guidance_type": guidance_type,
        "source": "action_agent",
    }
