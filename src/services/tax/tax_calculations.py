"""
Tax calculation logic extracted from TaxKnowledgeAgent.
"""

from typing import Dict, List, Optional, Any
from ...core.state import Message
from ...models.user import UserProfile as DBUserProfile
from ...core.logging import get_logger

logger = get_logger(__name__)


class TaxCalculator:
    """Handles tax calculations for the TaxKnowledgeAgent."""

    def __init__(self, tax_service):
        self.tax_service = tax_service

    async def perform_calculations(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Perform tax calculations if requested and data is available.
        """
        try:
            if not self._is_calculation_request(message.content):
                return None

            if not user_profile or not user_profile.annual_income:
                logger.info("Calculation requested but missing profile/income")
                return None

            # Determine calculation type
            calc_type = self._determine_calculation_type(message.content)
            
            if calc_type == "net_income":
                return await self._calculate_net_income(user_profile)
            elif calc_type == "tax_liability":
                return await self._calculate_tax_liability(user_profile)
            elif calc_type == "deduction_savings":
                return await self._calculate_deduction_savings(user_profile, context)
            else:
                return await self._calculate_comprehensive(user_profile)

        except Exception as e:
            logger.error(f"Tax calculation error: {e}")
            return None

    def _is_calculation_request(self, text: str) -> bool:
        """Check if user is requesting a calculation."""
        calc_keywords = [
            "calculate", "compute", "estimate", "how much",
            "net income", "take home", "tax liability", "savings"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in calc_keywords)

    def _determine_calculation_type(self, text: str) -> str:
        """Determine what type of calculation is being requested."""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ["net income", "take home", "after tax"]):
            return "net_income"
        elif any(term in text_lower for term in ["tax liability", "owe", "pay"]):
            return "tax_liability"
        elif any(term in text_lower for term in ["save", "deduction", "savings"]):
            return "deduction_savings"
        else:
            return "comprehensive"

    async def _calculate_net_income(self, user_profile: DBUserProfile) -> Dict[str, Any]:
        """Calculate net income after taxes."""
        try:
            gross_income = float(user_profile.annual_income or 0)
            
            # Basic German tax calculation (simplified)
            tax_free_allowance = 10908  # 2024 Grundfreibetrag
            taxable_income = max(0, gross_income - tax_free_allowance)
            
            # Progressive tax rates (simplified)
            tax_liability = self._calculate_progressive_tax(taxable_income)
            
            # Social contributions (approximate)
            social_contributions = gross_income * 0.20  # ~20% for social insurance
            
            net_income = gross_income - tax_liability - social_contributions
            
            return {
                "type": "net_income",
                "gross_income": gross_income,
                "tax_free_allowance": tax_free_allowance,
                "taxable_income": taxable_income,
                "tax_liability": tax_liability,
                "social_contributions": social_contributions,
                "net_income": net_income,
                "effective_tax_rate": (tax_liability / gross_income * 100) if gross_income > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Net income calculation error: {e}")
            return {}

    async def _calculate_tax_liability(self, user_profile: DBUserProfile) -> Dict[str, Any]:
        """Calculate tax liability only."""
        try:
            gross_income = float(user_profile.annual_income or 0)
            tax_free_allowance = 10908
            taxable_income = max(0, gross_income - tax_free_allowance)
            tax_liability = self._calculate_progressive_tax(taxable_income)
            
            return {
                "type": "tax_liability",
                "gross_income": gross_income,
                "taxable_income": taxable_income,
                "tax_liability": tax_liability,
                "marginal_tax_rate": self._get_marginal_rate(taxable_income),
            }
        except Exception as e:
            logger.error(f"Tax liability calculation error: {e}")
            return {}

    async def _calculate_deduction_savings(self, user_profile: DBUserProfile, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate potential savings from deductions."""
        try:
            # Get potential deductions
            potential_deductions = self._estimate_potential_deductions(user_profile)
            current_deductions = self._get_current_deductions(context)
            
            additional_deductions = max(0, potential_deductions - current_deductions)
            marginal_rate = self._get_marginal_rate(float(user_profile.annual_income or 0))
            tax_savings = additional_deductions * (marginal_rate / 100)
            
            return {
                "type": "deduction_savings",
                "current_deductions": current_deductions,
                "potential_deductions": potential_deductions,
                "additional_deductions": additional_deductions,
                "marginal_tax_rate": marginal_rate,
                "estimated_tax_savings": tax_savings,
            }
        except Exception as e:
            logger.error(f"Deduction savings calculation error: {e}")
            return {}

    async def _calculate_comprehensive(self, user_profile: DBUserProfile) -> Dict[str, Any]:
        """Comprehensive tax overview."""
        try:
            net_calc = await self._calculate_net_income(user_profile)
            tax_calc = await self._calculate_tax_liability(user_profile)
            
            return {
                "type": "comprehensive",
                **net_calc,
                "marginal_tax_rate": tax_calc.get("marginal_tax_rate", 0),
            }
        except Exception as e:
            logger.error(f"Comprehensive calculation error: {e}")
            return {}

    def _calculate_progressive_tax(self, taxable_income: float) -> float:
        """Calculate German progressive tax (simplified 2024 rates)."""
        if taxable_income <= 0:
            return 0
        elif taxable_income <= 15999:
            # Linear progression from 14% to 24%
            return taxable_income * 0.14 + (taxable_income - 10908) * 0.1 / 5091
        elif taxable_income <= 62809:
            # Linear progression from 24% to 42%
            return 2397 + (taxable_income - 15999) * 0.24 + (taxable_income - 15999) * 0.18 / 46810
        elif taxable_income <= 277825:
            # 42% rate
            return taxable_income * 0.42 - 9267
        else:
            # 45% top rate
            return taxable_income * 0.45 - 17602

    def _get_marginal_rate(self, income: float) -> float:
        """Get marginal tax rate for given income."""
        if income <= 10908:
            return 0
        elif income <= 15999:
            return 14 + (income - 10908) * 10 / 5091
        elif income <= 62809:
            return 24 + (income - 15999) * 18 / 46810
        elif income <= 277825:
            return 42
        else:
            return 45

    def _estimate_potential_deductions(self, user_profile: DBUserProfile) -> float:
        """Estimate potential deductions based on profile."""
        base_deductions = 1230  # Standard work expense allowance
        
        # Add estimated deductions based on employment
        if hasattr(user_profile, 'employment_status'):
            if user_profile.employment_status == "employed":
                base_deductions += 2000  # Estimated work expenses
            elif user_profile.employment_status == "self_employed":
                base_deductions += 5000  # Higher business expenses
        
        return base_deductions

    def _get_current_deductions(self, context: Dict[str, Any]) -> float:
        """Get current deductions from context."""
        # This would normally come from user's expense tracking
        return context.get("current_deductions", 1230)  # Default to standard allowance
