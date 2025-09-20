"""
Profile validation logic extracted from ProfileAgent.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from ...core.logging import get_logger

logger = get_logger(__name__)


class ProfileValidator:
    """Handles profile validation and consistency checks."""

    def validate_profile_updates(
        self,
        updates: Dict[str, Any],
        current_profile: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate profile updates for consistency and business rules.
        
        Returns:
            Tuple of (validated_updates, warnings)
        """
        try:
            validated = {}
            warnings = []

            # Validate each field
            for field, value in updates.items():
                validated_value, field_warnings = self._validate_field(field, value, current_profile)
                if validated_value is not None:
                    validated[field] = validated_value
                warnings.extend(field_warnings)

            # Cross-field validation
            cross_warnings = self._validate_cross_field_consistency(validated, current_profile)
            warnings.extend(cross_warnings)

            return validated, warnings

        except Exception as e:
            logger.error(f"Profile validation error: {e}")
            return updates, []

    def _validate_field(
        self,
        field: str,
        value: Any,
        current_profile: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, List[str]]:
        """Validate a single profile field."""
        warnings = []

        try:
            if field == "annual_income":
                return self._validate_income(value, warnings)
            
            elif field == "employment_status":
                return self._validate_employment_status(value, warnings)
            
            elif field == "filing_status":
                return self._validate_filing_status(value, warnings)
            
            elif field == "dependents":
                return self._validate_dependents(value, warnings)
            
            elif field == "name":
                return self._validate_name(value, warnings)
            
            elif field == "tax_goals":
                return self._validate_tax_goals(value, warnings)
            
            elif field == "risk_tolerance":
                return self._validate_risk_tolerance(value, warnings)
            
            elif field == "preferred_language":
                return self._validate_language(value, warnings)
            
            else:
                # Unknown field - pass through with warning
                warnings.append(f"Unknown profile field: {field}")
                return value, warnings

        except Exception as e:
            logger.error(f"Field validation error for {field}: {e}")
            warnings.append(f"Validation error for {field}")
            return None, warnings

    def _validate_income(self, value: Any, warnings: List[str]) -> Tuple[Optional[float], List[str]]:
        """Validate annual income."""
        try:
            if value is None:
                return None, warnings

            income = float(value)
            
            # Range validation
            if income < 0:
                warnings.append("Income cannot be negative")
                return None, warnings
            
            if income > 10000000:  # 10M EUR
                warnings.append("Income seems unusually high - please verify")
            
            if 0 < income < 1000:
                warnings.append("Income seems low - is this annual income?")

            return income, warnings

        except (ValueError, TypeError):
            warnings.append("Income must be a valid number")
            return None, warnings

    def _validate_employment_status(self, value: Any, warnings: List[str]) -> Tuple[Optional[str], List[str]]:
        """Validate employment status."""
        try:
            if value is None:
                return None, warnings

            status = str(value).lower()
            valid_statuses = ["employed", "self_employed", "unemployed", "student", "retired"]
            
            if status not in valid_statuses:
                warnings.append(f"Invalid employment status: {value}")
                return None, warnings

            return status, warnings

        except Exception:
            warnings.append("Employment status must be a valid string")
            return None, warnings

    def _validate_filing_status(self, value: Any, warnings: List[str]) -> Tuple[Optional[str], List[str]]:
        """Validate filing status."""
        try:
            if value is None:
                return None, warnings

            status = str(value).lower()
            valid_statuses = ["single", "married_jointly", "married_separately", "head_of_household"]
            
            if status not in valid_statuses:
                warnings.append(f"Invalid filing status: {value}")
                return None, warnings

            return status, warnings

        except Exception:
            warnings.append("Filing status must be a valid string")
            return None, warnings

    def _validate_dependents(self, value: Any, warnings: List[str]) -> Tuple[Optional[int], List[str]]:
        """Validate number of dependents."""
        try:
            if value is None:
                return None, warnings

            dependents = int(value)
            
            if dependents < 0:
                warnings.append("Number of dependents cannot be negative")
                return None, warnings
            
            if dependents > 20:
                warnings.append("Number of dependents seems unusually high")

            return dependents, warnings

        except (ValueError, TypeError):
            warnings.append("Number of dependents must be a valid integer")
            return None, warnings

    def _validate_name(self, value: Any, warnings: List[str]) -> Tuple[Optional[str], List[str]]:
        """Validate name."""
        try:
            if value is None:
                return None, warnings

            name = str(value).strip()
            
            if len(name) < 1:
                warnings.append("Name cannot be empty")
                return None, warnings
            
            if len(name) > 100:
                warnings.append("Name is too long")
                return None, warnings
            
            # Basic character validation
            if not name.replace(" ", "").replace("-", "").replace("'", "").isalpha():
                warnings.append("Name contains invalid characters")

            return name, warnings

        except Exception:
            warnings.append("Name must be a valid string")
            return None, warnings

    def _validate_tax_goals(self, value: Any, warnings: List[str]) -> Tuple[Optional[List[str]], List[str]]:
        """Validate tax goals."""
        try:
            if value is None:
                return None, warnings

            if not isinstance(value, list):
                warnings.append("Tax goals must be a list")
                return None, warnings

            valid_goals = ["save_money", "maximize_deductions", "simple_filing", "audit_protection"]
            validated_goals = []
            
            for goal in value:
                goal_str = str(goal).lower()
                if goal_str in valid_goals:
                    validated_goals.append(goal_str)
                else:
                    warnings.append(f"Invalid tax goal: {goal}")

            return validated_goals if validated_goals else None, warnings

        except Exception:
            warnings.append("Tax goals must be a valid list")
            return None, warnings

    def _validate_risk_tolerance(self, value: Any, warnings: List[str]) -> Tuple[Optional[str], List[str]]:
        """Validate risk tolerance."""
        try:
            if value is None:
                return None, warnings

            tolerance = str(value).lower()
            valid_tolerances = ["conservative", "moderate", "aggressive"]
            
            if tolerance not in valid_tolerances:
                warnings.append(f"Invalid risk tolerance: {value}")
                return None, warnings

            return tolerance, warnings

        except Exception:
            warnings.append("Risk tolerance must be a valid string")
            return None, warnings

    def _validate_language(self, value: Any, warnings: List[str]) -> Tuple[Optional[str], List[str]]:
        """Validate preferred language."""
        try:
            if value is None:
                return None, warnings

            lang = str(value).lower()
            valid_languages = ["en", "de"]
            
            if lang not in valid_languages:
                warnings.append(f"Invalid language: {value}")
                return None, warnings

            return lang, warnings

        except Exception:
            warnings.append("Language must be a valid string")
            return None, warnings

    def _validate_cross_field_consistency(
        self,
        updates: Dict[str, Any],
        current_profile: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Validate consistency across multiple fields."""
        warnings = []

        try:
            # Get combined profile (current + updates)
            combined = dict(current_profile or {})
            combined.update(updates)

            # Employment vs income consistency
            employment = combined.get("employment_status")
            income = combined.get("annual_income", 0)
            
            if employment == "unemployed" and income > 50000:
                warnings.append("High income reported for unemployed status - please verify")
            
            if employment == "student" and income > 30000:
                warnings.append("High income for student status - is this from part-time work?")
            
            if employment == "retired" and income > 100000:
                warnings.append("High income for retired status - is this from pensions/investments?")

            # Filing status vs dependents consistency
            filing_status = combined.get("filing_status")
            dependents = combined.get("dependents", 0)
            
            if filing_status == "single" and dependents > 0:
                warnings.append("Single filers with dependents may benefit from 'head of household' status")

            # Age-related consistency (if we had age data)
            # This could be extended with more sophisticated business rules

            return warnings

        except Exception as e:
            logger.error(f"Cross-field validation error: {e}")
            return warnings

    def check_profile_readiness_for_calculations(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Check if profile is ready for tax calculations."""
        try:
            missing_fields = []
            warnings = []
            
            # Required fields for basic calculations
            required_fields = {
                "annual_income": "Annual income is required for tax calculations",
                "filing_status": "Filing status affects tax rates and deductions",
                "employment_status": "Employment status determines available deductions"
            }

            for field, message in required_fields.items():
                if not profile.get(field):
                    missing_fields.append(field)
                    warnings.append(message)

            # Optional but recommended fields
            recommended_fields = {
                "dependents": "Number of dependents affects child-related benefits"
            }

            recommendations = []
            for field, message in recommended_fields.items():
                if profile.get(field) is None:
                    recommendations.append(message)

            return {
                "ready_for_calculations": len(missing_fields) == 0,
                "missing_required_fields": missing_fields,
                "warnings": warnings,
                "recommendations": recommendations,
                "completeness_percentage": self._calculate_readiness_percentage(profile)
            }

        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            return {
                "ready_for_calculations": False,
                "missing_required_fields": [],
                "warnings": [],
                "recommendations": [],
                "completeness_percentage": 0.0
            }

    def _calculate_readiness_percentage(self, profile: Dict[str, Any]) -> float:
        """Calculate what percentage of important fields are filled."""
        try:
            important_fields = [
                "annual_income", "filing_status", "employment_status", 
                "dependents", "name", "tax_goals"
            ]
            
            filled_count = sum(1 for field in important_fields if profile.get(field) is not None)
            return (filled_count / len(important_fields)) * 100

        except Exception as e:
            logger.error(f"Readiness percentage calculation error: {e}")
            return 0.0

    def suggest_profile_improvements(self, profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Suggest specific improvements to the profile."""
        try:
            suggestions = []

            # Income-related suggestions
            if not profile.get("annual_income"):
                suggestions.append({
                    "field": "annual_income",
                    "suggestion": "Add your annual income for personalized tax calculations",
                    "priority": "high"
                })

            # Employment-related suggestions
            if not profile.get("employment_status"):
                suggestions.append({
                    "field": "employment_status",
                    "suggestion": "Specify your employment status for relevant deduction recommendations",
                    "priority": "high"
                })

            # Filing status suggestions
            if not profile.get("filing_status"):
                suggestions.append({
                    "field": "filing_status",
                    "suggestion": "Set your filing status to get accurate tax calculations",
                    "priority": "high"
                })

            # Family-related suggestions
            if profile.get("dependents") is None:
                suggestions.append({
                    "field": "dependents",
                    "suggestion": "Add number of dependents to explore family tax benefits",
                    "priority": "medium"
                })

            # Goal-related suggestions
            if not profile.get("tax_goals"):
                suggestions.append({
                    "field": "tax_goals",
                    "suggestion": "Set your tax goals to receive personalized advice",
                    "priority": "low"
                })

            return suggestions

        except Exception as e:
            logger.error(f"Profile improvement suggestions error: {e}")
            return []
