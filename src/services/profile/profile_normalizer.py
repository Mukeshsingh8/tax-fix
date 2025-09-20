"""
Profile normalization logic extracted from ProfileAgent.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
from ...models.user import EmploymentStatus, FilingStatus
from ...core.helpers import extract_numbers
from ...utils import (
    normalize_employment_status, normalize_filing_status, 
    normalize_risk_tolerance, normalize_tax_goals, safe_float, safe_int
)
from ...core.logging import get_logger

logger = get_logger(__name__)


class ProfileNormalizer:
    """Handles profile data normalization and validation."""

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def extract_and_normalize_updates(
        self,
        message_content: str,
        current_profile: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Extract and normalize profile updates from user message.
        
        Returns:
            Tuple of (normalized_updates, change_summary)
        """
        try:
            # Extract raw updates using LLM
            raw_updates = await self._extract_profile_updates_llm(message_content)
            
            # Normalize the extracted updates
            normalized_updates = self._normalize_updates(raw_updates)
            
            # Create change summary
            change_summary = self._create_change_summary(normalized_updates, current_profile)
            
            return normalized_updates, change_summary

        except Exception as e:
            logger.error(f"Profile extraction error: {e}")
            return {}, []

    async def _extract_profile_updates_llm(self, message_content: str) -> Dict[str, Any]:
        """Use LLM to extract profile information from user message."""
        try:
            prompt = f"""Extract profile information from this user message. Return JSON only.

User message: "{message_content}"

Extract these fields if mentioned (return null if not found):
{{
  "name": "string or null",
  "annual_income": number or null,
  "employment_status": "employed|self_employed|unemployed|student|retired or null",
  "filing_status": "single|married_jointly|married_separately|head_of_household or null",
  "dependents": number or null,
  "tax_goals": ["save_money", "maximize_deductions", "simple_filing", "audit_protection"] or null,
  "risk_tolerance": "conservative|moderate|aggressive or null",
  "preferred_language": "en|de or null"
}}

Only extract explicitly mentioned information. Don't infer or assume."""

            messages = [
                {"role": "system", "content": "Extract profile data and return JSON only. No explanations."},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm_service.generate_json(
                messages=messages,
                model="groq",
                system_prompt=None,
                retries=2,
            )

            return response if isinstance(response, dict) else {}

        except Exception as e:
            logger.error(f"LLM profile extraction error: {e}")
            return self._fallback_extraction(message_content)

    def _fallback_extraction(self, message_content: str) -> Dict[str, Any]:
        """Fallback profile extraction using regex patterns."""
        try:
            updates = {}
            text = message_content.lower()

            # Extract income
            income_patterns = [
                r'(?:income|salary|earn).*?(\d+(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:euro|€|per year|annually)',
                r'make.*?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            ]
            for pattern in income_patterns:
                match = re.search(pattern, text)
                if match:
                    income_str = match.group(1).replace(',', '')
                    try:
                        updates["annual_income"] = float(income_str)
                        break
                    except ValueError:
                        continue

            # Extract employment status
            if any(word in text for word in ['employed', 'employee', 'work for', 'job']):
                updates["employment_status"] = "employed"
            elif any(word in text for word in ['self employed', 'freelance', 'contractor', 'business owner']):
                updates["employment_status"] = "self_employed"
            elif any(word in text for word in ['unemployed', 'jobless', 'looking for work']):
                updates["employment_status"] = "unemployed"
            elif any(word in text for word in ['student', 'studying', 'university']):
                updates["employment_status"] = "student"
            elif any(word in text for word in ['retired', 'retirement', 'pension']):
                updates["employment_status"] = "retired"

            # Extract filing status
            if any(word in text for word in ['married', 'spouse', 'husband', 'wife']):
                updates["filing_status"] = "married_jointly"
            elif any(word in text for word in ['single', 'unmarried', 'not married']):
                updates["filing_status"] = "single"

            # Extract dependents
            dependent_patterns = [
                r'(\d+)\s*(?:child|kid|dependent)',
                r'have\s*(\d+).*?(?:child|kid)',
                r'(\d+)\s*(?:son|daughter)',
            ]
            for pattern in dependent_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        updates["dependents"] = int(match.group(1))
                        break
                    except ValueError:
                        continue

            # Extract name (simple pattern)
            name_patterns = [
                r'(?:my name is|i am|i\'m|call me)\s+([a-zA-Z]+)',
                r'name:\s*([a-zA-Z]+)',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    updates["name"] = match.group(1).title()
                    break

            return updates

        except Exception as e:
            logger.error(f"Fallback extraction error: {e}")
            return {}

    def _normalize_updates(self, raw_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted profile updates."""
        try:
            normalized = {}

            # Name normalization
            if "name" in raw_updates and raw_updates["name"]:
                name = str(raw_updates["name"]).strip().title()
                if len(name) >= 2 and name.replace(" ", "").isalpha():
                    normalized["name"] = name

            # Income normalization
            if "annual_income" in raw_updates and raw_updates["annual_income"] is not None:
                income = safe_float(raw_updates["annual_income"])
                if income and 0 < income <= 10000000:  # Reasonable range
                    normalized["annual_income"] = income

            # Employment status normalization
            if "employment_status" in raw_updates and raw_updates["employment_status"]:
                emp_status = normalize_employment_status(raw_updates["employment_status"])
                if emp_status:
                    normalized["employment_status"] = emp_status

            # Filing status normalization
            if "filing_status" in raw_updates and raw_updates["filing_status"]:
                filing_status = normalize_filing_status(raw_updates["filing_status"])
                if filing_status:
                    normalized["filing_status"] = filing_status

            # Dependents normalization
            if "dependents" in raw_updates and raw_updates["dependents"] is not None:
                dependents = safe_int(raw_updates["dependents"])
                if dependents is not None and 0 <= dependents <= 20:  # Reasonable range
                    normalized["dependents"] = dependents

            # Tax goals normalization
            if "tax_goals" in raw_updates and raw_updates["tax_goals"]:
                goals = normalize_tax_goals(raw_updates["tax_goals"])
                if goals:
                    normalized["tax_goals"] = goals

            # Risk tolerance normalization
            if "risk_tolerance" in raw_updates and raw_updates["risk_tolerance"]:
                risk_tolerance = normalize_risk_tolerance(raw_updates["risk_tolerance"])
                if risk_tolerance:
                    normalized["risk_tolerance"] = risk_tolerance

            # Language normalization
            if "preferred_language" in raw_updates and raw_updates["preferred_language"]:
                lang = str(raw_updates["preferred_language"]).lower()
                if lang in ["en", "de", "english", "german"]:
                    normalized["preferred_language"] = "en" if lang in ["en", "english"] else "de"

            return normalized

        except Exception as e:
            logger.error(f"Normalization error: {e}")
            return {}

    def _create_change_summary(
        self,
        updates: Dict[str, Any],
        current_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Create a summary of profile changes."""
        try:
            changes = []

            for field, new_value in updates.items():
                old_value = current_profile.get(field) if current_profile else None
                
                if field == "annual_income":
                    if old_value != new_value:
                        from ...utils import format_currency
                        changes.append(f"Income: {format_currency(new_value)}")
                
                elif field == "employment_status":
                    if old_value != new_value:
                        readable = new_value.replace("_", " ").title()
                        changes.append(f"Employment: {readable}")
                
                elif field == "filing_status":
                    if old_value != new_value:
                        readable = new_value.replace("_", " ").title()
                        changes.append(f"Filing status: {readable}")
                
                elif field == "dependents":
                    if old_value != new_value:
                        changes.append(f"Dependents: {new_value}")
                
                elif field == "name":
                    if old_value != new_value:
                        changes.append(f"Name: {new_value}")
                
                elif field == "tax_goals":
                    if old_value != new_value:
                        goals_str = ", ".join(goal.replace("_", " ").title() for goal in new_value)
                        changes.append(f"Tax goals: {goals_str}")
                
                elif field == "risk_tolerance":
                    if old_value != new_value:
                        changes.append(f"Risk tolerance: {new_value.title()}")
                
                elif field == "preferred_language":
                    if old_value != new_value:
                        lang_name = "English" if new_value == "en" else "German"
                        changes.append(f"Language: {lang_name}")

            return changes

        except Exception as e:
            logger.error(f"Change summary error: {e}")
            return []

    def validate_profile_completeness(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile completeness and suggest missing fields."""
        try:
            missing_fields = []
            recommendations = []

            # Critical fields for tax calculations
            if not profile.get("annual_income"):
                missing_fields.append("annual_income")
                recommendations.append("Add your annual income for accurate tax calculations")

            if not profile.get("filing_status"):
                missing_fields.append("filing_status")
                recommendations.append("Specify your filing status (single, married, etc.)")

            if not profile.get("employment_status"):
                missing_fields.append("employment_status")
                recommendations.append("Tell us your employment status for relevant deductions")

            # Optional but helpful fields
            if profile.get("dependents") is None:
                recommendations.append("Add number of dependents for child-related deductions")

            if not profile.get("tax_goals"):
                recommendations.append("Set your tax goals to get personalized advice")

            completeness_score = self._calculate_completeness_score(profile)

            return {
                "completeness_score": completeness_score,
                "missing_critical_fields": missing_fields,
                "recommendations": recommendations,
                "is_ready_for_calculations": len(missing_fields) == 0
            }

        except Exception as e:
            logger.error(f"Profile validation error: {e}")
            return {
                "completeness_score": 0.0,
                "missing_critical_fields": [],
                "recommendations": [],
                "is_ready_for_calculations": False
            }

    def _calculate_completeness_score(self, profile: Dict[str, Any]) -> float:
        """Calculate profile completeness score (0.0 to 1.0)."""
        try:
            total_fields = 8  # Total important fields
            filled_fields = 0

            fields_to_check = [
                "name", "annual_income", "employment_status", "filing_status",
                "dependents", "tax_goals", "risk_tolerance", "preferred_language"
            ]

            for field in fields_to_check:
                value = profile.get(field)
                if value is not None and value != "" and value != []:
                    filled_fields += 1

            return filled_fields / total_fields

        except Exception as e:
            logger.error(f"Completeness calculation error: {e}")
            return 0.0

    def get_personalized_suggestions(self, profile: Dict[str, Any]) -> List[str]:
        """Get personalized suggestions based on profile."""
        try:
            suggestions = []

            # Income-based suggestions
            income = profile.get("annual_income", 0)
            if income > 60000:
                suggestions.append("Consider maximizing pension contributions for tax benefits")
            elif income < 25000:
                suggestions.append("Check if you qualify for additional tax credits")

            # Employment-based suggestions
            employment = profile.get("employment_status")
            if employment == "employed":
                suggestions.append("Track commuting and work-related expenses for deductions")
            elif employment == "self_employed":
                suggestions.append("Keep detailed records of business expenses")

            # Family-based suggestions
            dependents = profile.get("dependents", 0)
            if dependents > 0:
                suggestions.append(f"With {dependents} dependent(s), explore childcare and education deductions")

            # Goal-based suggestions
            goals = profile.get("tax_goals", [])
            if "maximize_deductions" in goals:
                suggestions.append("Review all available deduction categories")
            if "simple_filing" in goals:
                suggestions.append("Consider using standard deductions for simplicity")

            return suggestions[:3]  # Return top 3 suggestions

        except Exception as e:
            logger.error(f"Personalized suggestions error: {e}")
            return []
