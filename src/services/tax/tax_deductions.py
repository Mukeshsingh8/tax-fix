"""
Tax deduction analysis logic extracted from TaxKnowledgeAgent.
"""

from typing import Dict, List, Optional, Any
from ...core.state import Message
from ...models.user import UserProfile as DBUserProfile
from ...core.logging import get_logger

logger = get_logger(__name__)


class TaxDeductionAnalyzer:
    """Handles deduction analysis for the TaxKnowledgeAgent."""

    def __init__(self, tax_service, llm_service):
        self.tax_service = tax_service
        self.llm_service = llm_service

    async def identify_relevant_deductions(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        relevant_content: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify and rank deductions relevant to the user's query and profile.
        """
        try:
            deductions = relevant_content.get("deductions", [])
            if not deductions:
                return []

            # Score deductions based on relevance
            scored_deductions = []
            for deduction in deductions:
                score = await self.score_deduction_relevance(
                    deduction, message, user_profile
                )
                if score > 0.3:  # Relevance threshold
                    scored_deductions.append({
                        **deduction,
                        "relevance_score": score
                    })

            # Sort by relevance and return top 5
            scored_deductions.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_deductions[:5]

        except Exception as e:
            self.logger.error(f"Deduction identification error: {e}")
            return []

    async def score_deduction_relevance(
        self,
        deduction: Dict[str, Any],
        message: Message,
        user_profile: Optional[DBUserProfile]
    ) -> float:
        """Score how relevant a deduction is to the user's query and profile."""
        try:
            score = 0.0
            query_lower = message.content.lower()
            
            # Check if deduction matches query keywords
            deduction_name = deduction.get("name", "").lower()
            deduction_desc = deduction.get("description", "").lower()
            
            if any(word in deduction_name for word in query_lower.split()):
                score += 0.8
            elif any(word in deduction_desc for word in query_lower.split()):
                score += 0.5

            # Score based on profile compatibility
            if user_profile:
                profile_score = self.score_profile_compatibility(deduction, user_profile)
                score += profile_score * 0.4

            # Score based on common usage
            category = deduction.get("category", "")
            if category in ["work_expenses", "home_office", "education"]:
                score += 0.2

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"Deduction scoring error: {e}")
            return 0.0

    def score_profile_compatibility(
        self,
        deduction: Dict[str, Any],
        user_profile: DBUserProfile
    ) -> float:
        """Score how compatible a deduction is with the user's profile."""
        score = 0.0
        
        # Employment status compatibility
        employment = getattr(user_profile, 'employment_status', None)
        category = deduction.get("category", "")
        
        if employment == "employed" and category == "work_expenses":
            score += 0.8
        elif employment == "self_employed" and category == "business_expenses":
            score += 0.9
        elif employment == "unemployed" and category == "job_search":
            score += 0.7

        # Income level compatibility
        income = getattr(user_profile, 'annual_income', 0)
        if income:
            max_amount = deduction.get("max_amount", 0)
            if max_amount and income > max_amount * 10:  # High earner
                score += 0.3
            elif max_amount and income < max_amount * 5:  # Lower income
                score += 0.1

        # Dependents compatibility
        dependents = getattr(user_profile, 'dependents', 0)
        if dependents > 0 and category in ["childcare", "education", "family"]:
            score += 0.6

        return score

    async def get_personalized_deduction_suggestions(
        self,
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Get personalized deduction suggestions based on profile."""
        try:
            suggestions = []
            
            if not user_profile:
                return self.get_generic_suggestions()

            employment = getattr(user_profile, 'employment_status', None)
            income = getattr(user_profile, 'annual_income', 0)
            dependents = getattr(user_profile, 'dependents', 0)

            # Employment-based suggestions
            if employment == "employed":
                suggestions.extend([
                    {
                        "category": "Commuting",
                        "suggestion": "Track your commute costs - you can deduct €0.30 per km (first 20km) and €0.38 per km (beyond 20km) for work trips.",
                        "priority": "high"
                    },
                    {
                        "category": "Home Office",
                        "suggestion": "If you work from home, you can deduct home office expenses up to €1,260 per year.",
                        "priority": "medium"
                    }
                ])

            if employment == "self_employed":
                suggestions.extend([
                    {
                        "category": "Business Expenses",
                        "suggestion": "Keep receipts for all business-related purchases, travel, and equipment.",
                        "priority": "high"
                    },
                    {
                        "category": "Professional Development",
                        "suggestion": "Training courses and professional certifications are fully deductible.",
                        "priority": "medium"
                    }
                ])

            # Family-based suggestions
            if dependents > 0:
                suggestions.extend([
                    {
                        "category": "Childcare",
                        "suggestion": f"With {dependents} dependent(s), you can deduct up to €4,000 per child for childcare costs.",
                        "priority": "high"
                    },
                    {
                        "category": "Education",
                        "suggestion": "School fees, tutoring, and educational materials may be deductible.",
                        "priority": "medium"
                    }
                ])

            # Income-based suggestions
            if income and income > 50000:
                suggestions.append({
                    "category": "Pension Contributions",
                    "suggestion": "Consider maximizing your pension contributions - they're tax-deductible up to certain limits.",
                    "priority": "medium"
                })

            return suggestions

        except Exception as e:
            self.logger.error(f"Personalized suggestions error: {e}")
            return self.get_generic_suggestions()

    def get_generic_suggestions(self) -> List[Dict[str, str]]:
        """Get generic deduction suggestions."""
        return [
            {
                "category": "Work Expenses",
                "suggestion": "Track work-related expenses like tools, uniforms, and professional development.",
                "priority": "high"
            },
            {
                "category": "Health Insurance",
                "suggestion": "Private health insurance premiums are generally deductible.",
                "priority": "medium"
            },
            {
                "category": "Donations",
                "suggestion": "Charitable donations up to 20% of your income are tax-deductible.",
                "priority": "low"
            }
        ]

    async def analyze_deduction_potential(
        self,
        user_profile: Optional[DBUserProfile],
        current_expenses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze the user's deduction potential."""
        try:
            current_total = sum(expense.get("amount", 0) for expense in current_expenses)
            potential_total = self.estimate_potential_deductions(user_profile)
            
            return {
                "current_deductions": current_total,
                "potential_deductions": potential_total,
                "missed_opportunities": max(0, potential_total - current_total),
                "optimization_percentage": (current_total / potential_total * 100) if potential_total > 0 else 0,
                "recommendations": await self.get_personalized_deduction_suggestions(user_profile, {})
            }

        except Exception as e:
            self.logger.error(f"Deduction analysis error: {e}")
            return {}

    def estimate_potential_deductions(self, user_profile: Optional[DBUserProfile]) -> float:
        """Estimate potential deductions based on profile."""
        if not user_profile:
            return 1230  # Standard work expense allowance

        base = 1230
        employment = getattr(user_profile, 'employment_status', None)
        income = getattr(user_profile, 'annual_income', 0)
        dependents = getattr(user_profile, 'dependents', 0)

        # Employment-based estimates
        if employment == "employed":
            base += 2500  # Commuting, home office, tools
        elif employment == "self_employed":
            base += income * 0.15 if income else 5000  # Business expenses

        # Family-based estimates
        if dependents > 0:
            base += dependents * 2000  # Childcare, education

        # Income-based estimates
        if income and income > 60000:
            base += 3000  # Higher earners typically have more deductible expenses

        return base
