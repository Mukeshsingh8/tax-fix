"""Profile agent for managing user profiles and personalization."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.state import Message, AgentResponse, AgentType
from ..models.user import UserProfile
from ..utils import safe_agent_method
from .base import BaseAgent
from ..services.profile_service import ProfileService


class ProfileAgent(BaseAgent):
    """Profile agent that manages user profiles and personalization."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.PROFILE, *args, **kwargs)
        self.profile_service = ProfileService(self.llm_service, self.database_service)

    async def get_system_prompt(self) -> str:
        return """
        You are the Profile Agent for the TaxFix system. Your role is to:
        1) Extract and update user profile information (income, filing status, dependents, employment status, preferences)
        2) Ask clarifying questions when info is incomplete
        3) Learn user preferences (goals, risk tolerance, style)
        4) Provide personalized next steps
        IMPORTANT:
        - Always respond in English.
        - Prefer concrete, structured updates over long prose.
        - Keep suggestions actionable.
        """

    @safe_agent_method(
        fallback_content="I can help manage your profile information for better tax advice. What would you like to update?",
        fallback_confidence=0.5
    )
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process profile-related requests."""
        user_id = context.get("user_id")
        if not user_id:
            return await self.create_response(
                content="I need to know who you are to update your profile.",
                confidence=0.0
            )

        text = (message.content or "").strip()
        
        # Handle different profile request types
        if "update profile" in text.lower() or "my profile" in text.lower():
            return await self._handle_profile_update_request(text, user_id)
        elif "my details" in text.lower() or "my information" in text.lower():
            return await self._provide_profile_summary(user_id)
        elif "create profile" in text.lower():
            return await self._handle_profile_creation_request(text, user_id)
        elif "help with profile" in text.lower():
            return await self._provide_profile_help()
        else:
            # Try to extract and update profile information passively
            return await self._handle_passive_profile_update(text, user_id)

    async def _handle_profile_update_request(self, text: str, user_id: str) -> AgentResponse:
        """Handle explicit requests to update profile."""
        # Extract profile information from text
        extracted_info = await self.profile_service.extract_profile_info(text)
        
        if not extracted_info:
            return await self.create_response(
                content="What specific profile information would you like to update? Please provide details like your income, employment status, or number of dependents.",
                confidence=0.7,
                reasoning="User wants to update profile but provided no specific details."
            )

        # Update profile using the unified service
        updated_profile = await self.profile_service.update_user_profile(user_id, extracted_info)
        
        if updated_profile:
            return await self.create_response(
                content="Your profile has been updated successfully!",
                confidence=0.9,
                metadata={"updated_profile": self._profile_to_dict(updated_profile)},
                reasoning="Profile updated using ProfileService."
            )
        else:
            return await self.create_response(
                content="I had trouble updating your profile. Please try again.",
                confidence=0.4,
                reasoning="Profile update failed."
            )

    async def _handle_profile_creation_request(self, text: str, user_id: str) -> AgentResponse:
        """Handle requests to create a new profile."""
        # Extract profile information from text
        extracted_info = await self.profile_service.extract_profile_info(text)
        
        if not extracted_info:
            return await self.create_response(
                content="To create your profile, please provide some initial details like your annual income, employment status, and number of dependents.",
                confidence=0.7,
                reasoning="User wants to create profile but provided no details."
            )

        # Create new profile
        new_profile = await self.profile_service.create_user_profile(user_id, extracted_info)
        
        if new_profile:
            return await self.create_response(
                content="Your new profile has been created successfully!",
                confidence=0.9,
                metadata={"new_profile": self._profile_to_dict(new_profile)},
                reasoning="New profile created using ProfileService."
            )
        else:
            return await self.create_response(
                content="I had trouble creating your profile. Please try again.",
                confidence=0.4,
                reasoning="Profile creation failed."
            )

    async def _handle_passive_profile_update(self, text: str, user_id: str) -> AgentResponse:
        """Handle passive profile updates from conversation."""
        # Extract and update profile in one operation
        updated_profile, warnings = await self.profile_service.extract_and_update_profile(user_id, text)
        
        if updated_profile:
            warning_text = f" Note: {'; '.join(warnings)}" if warnings else ""
            return await self.create_response(
                content=f"I've updated your profile with the new information you provided.{warning_text}",
                confidence=0.8,
                metadata={"updated_profile": self._profile_to_dict(updated_profile)},
                reasoning="Profile updated passively from conversation."
            )
        else:
            return await self.create_response(
                content="I can help manage your profile information for better tax advice. What would you like to update?",
                confidence=0.5,
                reasoning="No profile information extracted from message."
            )

    async def _provide_profile_summary(self, user_id: str) -> AgentResponse:
        """Provide a summary of the user's current profile."""
        current_profile = await self.profile_service.get_user_profile(user_id)
        
        if not current_profile:
            return await self.create_response(
                content="I don't have a complete profile for you yet. Would you like to create one?",
                confidence=0.6,
                reasoning="User requested profile summary but no profile exists."
            )

        profile_dict = self._profile_to_dict(current_profile)
        summary_content = "Here is your current profile information:\n\n"
        
        for key, value in profile_dict.items():
            if value is not None and value != [] and key not in ['user_id', 'created_at', 'updated_at']:
                display_key = key.replace('_', ' ').title()
                summary_content += f"- **{display_key}**: {value}\n"

        return await self.create_response(
            content=summary_content,
            confidence=0.85,
            metadata={"profile_summary": profile_dict},
            reasoning="Provided user profile summary."
        )

    async def _provide_profile_help(self) -> AgentResponse:
        """Provide guidance on profile management."""
        help_content = """I can help you manage your tax profile in several ways:

**Profile Information I can track:**
- Annual income and employment status
- Filing status (single, married, etc.)
- Number of dependents/children
- Tax goals and risk tolerance
- Communication preferences

**How to update your profile:**
- Just tell me: "I earn €50,000 per year" or "I'm married with 2 children"
- Ask to see your current info: "Show me my profile"
- Request specific updates: "Update my employment status to self-employed"

What would you like to update or learn about?"""

        return await self.create_response(
            content=help_content,
            confidence=0.9,
            reasoning="Provided profile management help."
        )

    def _profile_to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """Convert UserProfile object to dictionary."""
        try:
            if not profile:
                return {}

            return {
                "user_id": profile.user_id,
                "annual_income": profile.annual_income,
                "employment_status": profile.employment_status,
                "filing_status": profile.filing_status,
                "dependents": profile.dependents,
                "tax_goals": profile.tax_goals or [],
                "risk_tolerance": profile.risk_tolerance,
                "preferred_deductions": profile.preferred_deductions or [],
                "conversation_count": profile.conversation_count,
                "last_interaction": profile.last_interaction,
                "preferred_communication_style": profile.preferred_communication_style,
                "tax_complexity_level": profile.tax_complexity_level,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            }

        except Exception as e:
            self.logger.error(f"Profile conversion error: {e}")
            return {}