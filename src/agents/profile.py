"""Profile agent for managing user profiles and personalization."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.state import Message, AgentResponse, AgentType
from ..models.user import UserProfile
from ..utils import safe_agent_method
from .base import BaseAgent
from ..services.profile.profile_normalizer import ProfileNormalizer
from ..services.profile.profile_validator import ProfileValidator


class ProfileAgent(BaseAgent):
    """Profile agent that manages user profiles and personalization."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.PROFILE, *args, **kwargs)
        self.normalizer = ProfileNormalizer(self.llm_service)
        self.validator = ProfileValidator()

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

        # Get current profile
        current_profile = await self.database_service.get_user_profile(user_id)
        current_dict = self._profile_to_dict(current_profile) if current_profile else {}

        # Extract and normalize updates
        updates, change_summary = await self.normalizer.extract_and_normalize_updates(
            message.content, current_dict
        )

        if not updates:
            return await self._handle_no_updates_found(message.content, current_dict)

        # Validate updates
        validated_updates, warnings = self.validator.validate_profile_updates(updates, current_dict)

        if not validated_updates:
            return await self._handle_validation_failed(warnings)

        # Apply updates to database
        success = await self._update_profile_in_database(user_id, validated_updates)

        if not success:
            return await self.create_response(
                content="I had trouble updating your profile. Please try again.",
                confidence=0.2,
                reasoning="Database update failed"
            )

        # Create success response
        return await self._create_update_success_response(
            change_summary, warnings, validated_updates, user_id
        )

    async def _handle_no_updates_found(
        self,
        message_content: str,
        current_profile: Dict[str, Any]
    ) -> AgentResponse:
        """Handle case where no profile updates were found."""
        try:
            # Check if user is asking for profile info
            if any(word in message_content.lower() for word in ["profile", "info", "about me", "my details"]):
                return await self._provide_profile_summary(current_profile)

            # Check if user needs help with profile
            if any(word in message_content.lower() for word in ["help", "how", "what"]):
                return await self._provide_profile_help()

            # Default response
            return await self.create_response(
                content="I didn't find any profile information to update. You can tell me about your income, job, family situation, or tax goals.",
                confidence=0.70,
                reasoning="No clear profile updates extracted",
                suggested_actions=[
                    {"action": "update_income", "description": "Update your income"},
                    {"action": "update_employment", "description": "Update employment status"},
                    {"action": "view_profile", "description": "View current profile"},
                ],
            )

        except Exception as e:
            self.logger.error(f"No updates handler error: {e}")
            return await self.create_response(
                content="I can help update your profile information. What would you like to change?",
                confidence=0.5,
                reasoning="Error in no-updates handler"
            )

    async def _handle_validation_failed(self, warnings: List[str]) -> AgentResponse:
        """Handle case where validation failed."""
        try:
            warning_text = "; ".join(warnings[:3])  # Show first 3 warnings
            content = f"I had trouble processing that information: {warning_text}. Please check your details and try again."
            
            return await self.create_response(
                content=content,
                confidence=0.3,
                reasoning="Profile validation failed",
                metadata={"validation_warnings": warnings}
            )

        except Exception as e:
            self.logger.error(f"Validation failed handler error: {e}")
            return await self.create_response(
                content="There was an issue with the information provided. Please check and try again.",
                confidence=0.2,
                reasoning="Validation error"
            )

    async def _update_profile_in_database(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update profile in database."""
        try:
            # Get current profile or create new one
            current_profile = await self.database_service.get_user_profile(user_id)
            
            if current_profile:
                # Update existing profile
                for field, value in updates.items():
                    if hasattr(current_profile, field):
                        setattr(current_profile, field, value)
                
                updated_profile = await self.database_service.update_user_profile(user_id, current_profile)
                return updated_profile is not None
            else:
                # Create new profile
                profile_data = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    **updates
                }
                new_profile = await self.database_service.create_user_profile(**profile_data)
                return new_profile is not None

        except Exception as e:
            self.logger.error(f"Database update error: {e}")
            return False

    async def _create_update_success_response(
        self,
        change_summary: List[str],
        warnings: List[str],
        updates: Dict[str, Any],
        user_id: str
    ) -> AgentResponse:
        """Create success response for profile updates."""
        try:
            # Build main content
            if change_summary:
                changes_text = ", ".join(change_summary)
                content = f"✅ Updated your profile: {changes_text}."
            else:
                content = "✅ Your profile has been updated."

            # Add warnings if any
            if warnings:
                warning_text = "; ".join(warnings[:2])
                content += f" Note: {warning_text}"

            # Get updated profile for suggestions
            updated_profile = await self.database_service.get_user_profile(user_id)
            profile_dict = self._profile_to_dict(updated_profile) if updated_profile else {}

            # Check completeness and get suggestions
            readiness = self.validator.check_profile_readiness_for_calculations(profile_dict)
            suggestions = self.validator.suggest_profile_improvements(profile_dict)

            # Add completeness info
            if not readiness["ready_for_calculations"]:
                missing_count = len(readiness["missing_required_fields"])
                content += f" Your profile is {readiness['completeness_percentage']:.0f}% complete."
                if missing_count > 0:
                    content += f" Add {missing_count} more field(s) for full tax calculations."

            # Create suggested actions
            suggested_actions = []
            for suggestion in suggestions[:3]:
                suggested_actions.append({
                    "action": f"update_{suggestion['field']}",
                    "description": suggestion['suggestion']
                })

            if not suggested_actions:
                suggested_actions = [
                    {"action": "view_profile", "description": "View complete profile"},
                    {"action": "calculate_taxes", "description": "Calculate your taxes"},
                ]

            return await self.create_response(
                content=content,
                confidence=0.9,
                reasoning="Profile successfully updated",
                suggested_actions=suggested_actions,
                metadata={
                    "updated_fields": list(updates.keys()),
                    "profile_completeness": readiness["completeness_percentage"],
                    "ready_for_calculations": readiness["ready_for_calculations"],
                    "warnings": warnings
                }
            )

        except Exception as e:
            self.logger.error(f"Success response creation error: {e}")
            return await self.create_response(
                content="✅ Your profile has been updated successfully.",
                confidence=0.8,
                reasoning="Profile updated with error in response creation"
            )

    async def _provide_profile_summary(self, profile: Dict[str, Any]) -> AgentResponse:
        """Provide a summary of the current profile."""
        try:
            if not profile:
                return await self.create_response(
                    content="You don't have a profile set up yet. I can help you create one! Tell me about your income, job, and family situation.",
                    confidence=0.8,
                    reasoning="No profile found",
                    suggested_actions=[
                        {"action": "setup_profile", "description": "Set up your profile"},
                    ]
                )

            # Build profile summary
            summary_parts = []
            
            if profile.get("name"):
                summary_parts.append(f"Name: {profile['name']}")
            
            if profile.get("annual_income"):
                from ..utils import format_currency
                summary_parts.append(f"Income: {format_currency(profile['annual_income'])}")
            
            if profile.get("employment_status"):
                emp_status = profile["employment_status"].replace("_", " ").title()
                summary_parts.append(f"Employment: {emp_status}")
            
            if profile.get("filing_status"):
                filing_status = profile["filing_status"].replace("_", " ").title()
                summary_parts.append(f"Filing: {filing_status}")
            
            if profile.get("dependents") is not None:
                summary_parts.append(f"Dependents: {profile['dependents']}")

            if summary_parts:
                content = "**Your Profile:**\n" + "\n".join(f"• {part}" for part in summary_parts)
            else:
                content = "Your profile is mostly empty. Let's add some information!"

            # Add completeness info
            readiness = self.validator.check_profile_readiness_for_calculations(profile)
            content += f"\n\nProfile completeness: {readiness['completeness_percentage']:.0f}%"

            return await self.create_response(
                content=content,
                confidence=0.95,
                reasoning="Profile summary provided",
                suggested_actions=[
                    {"action": "update_profile", "description": "Update profile information"},
                    {"action": "calculate_taxes", "description": "Calculate taxes with current profile"},
                ],
                metadata={
                    "profile_completeness": readiness["completeness_percentage"],
                    "ready_for_calculations": readiness["ready_for_calculations"]
                }
            )

        except Exception as e:
            self.logger.error(f"Profile summary error: {e}")
            return await self.create_response(
                content="I can show you your profile information. What specific details would you like to know?",
                confidence=0.5,
                reasoning="Error in profile summary"
            )

    async def _provide_profile_help(self) -> AgentResponse:
        """Provide help about profile management."""
        try:
            content = """I can help you manage your profile for personalized tax advice. You can tell me:

• **Income**: "I make €50,000 per year"
• **Employment**: "I'm employed" or "I'm self-employed"
• **Family**: "I'm married with 2 children"
• **Goals**: "I want to maximize deductions"

Just tell me about your situation in natural language, and I'll update your profile accordingly."""

            return await self.create_response(
                content=content,
                confidence=0.95,
                reasoning="Profile help provided",
                suggested_actions=[
                    {"action": "setup_income", "description": "Tell me your income"},
                    {"action": "setup_employment", "description": "Tell me about your job"},
                    {"action": "setup_family", "description": "Tell me about your family"},
                ],
            )

        except Exception as e:
            self.logger.error(f"Profile help error: {e}")
            return await self.create_response(
                content="I can help you set up and manage your profile. What would you like to know?",
                confidence=0.5,
                reasoning="Error in profile help"
            )

    def _profile_to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """Convert UserProfile object to dictionary."""
        try:
            if not profile:
                return {}

            return {
                "name": profile.name,
                "annual_income": profile.annual_income,
                "employment_status": profile.employment_status,
                "filing_status": profile.filing_status,
                "dependents": profile.dependents,
                "tax_goals": profile.tax_goals or [],
                "risk_tolerance": profile.risk_tolerance,
                "preferred_language": profile.preferred_language,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            }

        except Exception as e:
            self.logger.error(f"Profile conversion error: {e}")
            return {}
