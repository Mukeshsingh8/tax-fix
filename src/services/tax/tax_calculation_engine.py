"""
Tax Calculation Engine - Handles German tax calculations and computations.
Extracted from TaxKnowledgeService to follow single responsibility principle.
"""

from typing import Dict, Any, Optional
from ...models.tax_knowledge import GermanTaxBreakdown
from ..base_service import BaseService


class TaxCalculationEngine(BaseService):
    """
    German tax calculation engine.
    
    Responsibilities:
    - German income tax calculations (2024 rules)
    - Social security contributions
    - Tax optimization calculations
    - Various tax scenarios and breakdowns
    """
    
    def __init__(self):
        super().__init__("TaxCalculationEngine")
        
        # German tax constants for 2024
        self.GRUNDFREIBETRAG = 11604  # Basic allowance
        self.WERBUNGSKOSTEN_PAUSCHALE = 1230  # Work expense allowance
        self.SONDERAUSGABEN_PAUSCHALE = 36  # Special expenses allowance
        
        # Tax brackets (simplified 2024)
        self.TAX_BRACKETS = [
            {"min": 0, "max": 11604, "rate": 0.0},           # Tax-free
            {"min": 11604, "max": 17005, "rate": 0.14},     # Entry rate
            {"min": 17005, "max": 66760, "rate": 0.24},     # Progressive zone 1
            {"min": 66760, "max": 277825, "rate": 0.42},    # Main zone
            {"min": 277825, "max": float("inf"), "rate": 0.45}  # Top rate
        ]
    
    def calculate_german_tax(
        self,
        income: float,
        filing_status: str = "single",
        dependents: int = 0,
        health_insurance_type: str = "statutory",
        age: int = 30,
        has_children: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive German tax breakdown.
        
        Args:
            income: Annual gross income in EUR
            filing_status: 'single', 'married_jointly', 'married_separately'
            dependents: Number of dependent children
            health_insurance_type: 'statutory' or 'private'
            age: Age for pension contribution calculations
            has_children: Whether the taxpayer has children
            
        Returns:
            Comprehensive tax calculation breakdown
        """
        self.log_operation_start(
            "calculate_german_tax", 
            income=income, 
            filing_status=filing_status,
            dependents=dependents
        )
        
        try:
            # Input validation
            if income < 0:
                raise ValueError("Income cannot be negative")
            if dependents < 0:
                raise ValueError("Dependents cannot be negative")
            
            # Calculate components
            result = {
                "gross_income": income,
                "filing_status": filing_status,
                "dependents": dependents,
                "basic_allowance": self.get_basic_allowance(filing_status),
                "work_expenses": self.calculate_work_expenses(income),
                "special_expenses": self.calculate_special_expenses(income, health_insurance_type),
                "child_allowances": self.calculate_child_allowances(dependents),
                "taxable_income": 0.0,
                "income_tax": 0.0,
                "solidarity_surcharge": 0.0,
                "church_tax": 0.0,
                "social_security": self.calculate_social_security(income, age),
                "total_tax_burden": 0.0,
                "net_income": 0.0,
                "effective_tax_rate": 0.0,
                "marginal_tax_rate": 0.0,
            }
            
            # Calculate taxable income
            result["taxable_income"] = max(0, income - result["basic_allowance"] - 
                                         result["work_expenses"] - result["special_expenses"] - 
                                         result["child_allowances"])
            
            # Calculate income tax
            result["income_tax"] = self.calculate_income_tax(result["taxable_income"])
            
            # Calculate solidarity surcharge (5.5% of income tax, with exemption)
            result["solidarity_surcharge"] = self.calculate_solidarity_surcharge(result["income_tax"])
            
            # Calculate church tax (8-9% of income tax, assuming 9% average)
            result["church_tax"] = result["income_tax"] * 0.09
            
            # Calculate totals
            result["total_tax_burden"] = (result["income_tax"] + result["solidarity_surcharge"] + 
                                        result["church_tax"] + result["social_security"]["total"])
            
            result["net_income"] = income - result["total_tax_burden"]
            
            # Calculate rates
            if income > 0:
                result["effective_tax_rate"] = (result["total_tax_burden"] / income) * 100
                result["marginal_tax_rate"] = self.calculate_marginal_rate(result["taxable_income"]) * 100
            
            self.log_operation_success(
                "calculate_german_tax", 
                f"net_income={result['net_income']:.2f}, effective_rate={result['effective_tax_rate']:.1f}%"
            )
            
            return result
            
        except Exception as e:
            self.log_operation_error("calculate_german_tax", e)
            # Return basic fallback calculation
            return self.create_fallback_calculation(income, filing_status, dependents)
    
    def calculate_net_income(self, gross_income: float, **kwargs) -> float:
        """
        Quick calculation of net income from gross.
        
        Args:
            gross_income: Annual gross income
            **kwargs: Additional parameters for detailed calculation
            
        Returns:
            Estimated net income
        """
        try:
            calculation = self.calculate_german_tax(gross_income, **kwargs)
            return calculation["net_income"]
        except Exception as e:
            self.logger.warning(f"Net income calculation failed: {e}")
            # Simple fallback: assume 30% total tax burden
            return gross_income * 0.7
    
    def calculate_tax_savings(self, current_income: float, deduction_amount: float) -> Dict[str, float]:
        """
        Calculate potential tax savings from a deduction.
        
        Args:
            current_income: Current annual income
            deduction_amount: Amount of potential deduction
            
        Returns:
            Dictionary with savings breakdown
        """
        try:
            # Calculate current tax
            current_calc = self.calculate_german_tax(current_income)
            
            # Calculate tax with deduction
            reduced_calc = self.calculate_german_tax(current_income - deduction_amount)
            
            return {
                "deduction_amount": deduction_amount,
                "tax_savings": current_calc["total_tax_burden"] - reduced_calc["total_tax_burden"],
                "net_benefit": reduced_calc["net_income"] - current_calc["net_income"],
                "effective_savings_rate": ((current_calc["total_tax_burden"] - reduced_calc["total_tax_burden"]) / deduction_amount) * 100 if deduction_amount > 0 else 0
            }
        except Exception as e:
            self.logger.warning(f"Tax savings calculation failed: {e}")
            return {"deduction_amount": deduction_amount, "tax_savings": 0, "net_benefit": 0, "effective_savings_rate": 0}
    
    def get_basic_allowance(self, filing_status: str) -> float:
        """Get basic tax allowance based on filing status."""
        if filing_status == "married_jointly":
            return self.GRUNDFREIBETRAG * 2
        return self.GRUNDFREIBETRAG
    
    def calculate_work_expenses(self, income: float) -> float:
        """Calculate work-related expense deductions."""
        # For simplicity, return the standard deduction
        # In practice, this could be higher if actual expenses exceed the standard
        return self.WERBUNGSKOSTEN_PAUSCHALE
    
    def calculate_special_expenses(self, income: float, health_insurance_type: str) -> float:
        """Calculate special expenses (health insurance, etc.)."""
        if health_insurance_type == "statutory":
            # Simplified: assume standard health insurance contribution
            return min(income * 0.073, 4987.5)  # Max health insurance contribution for 2024
        else:
            # Private insurance - use standard deduction
            return self.SONDERAUSGABEN_PAUSCHALE
    
    def calculate_child_allowances(self, dependents: int) -> float:
        """Calculate child allowances and benefits."""
        # Kinderfreibetrag for 2024: €6,384 per child
        return dependents * 6384
    
    def calculate_income_tax(self, taxable_income: float) -> float:
        """Calculate income tax using German tax brackets."""
        if taxable_income <= 0:
            return 0
        
        tax = 0.0
        remaining_income = taxable_income
        
        for bracket in self.TAX_BRACKETS:
            if remaining_income <= 0:
                break
            
            bracket_min = bracket["min"]
            bracket_max = bracket["max"]
            rate = bracket["rate"]
            
            # Calculate taxable amount in this bracket
            if remaining_income + sum(b["max"] - b["min"] for b in self.TAX_BRACKETS[:self.TAX_BRACKETS.index(bracket)] if b["max"] != float("inf")) > bracket_min:
                taxable_in_bracket = min(remaining_income, bracket_max - bracket_min)
                tax += taxable_in_bracket * rate
                remaining_income -= taxable_in_bracket
        
        return tax
    
    def calculate_solidarity_surcharge(self, income_tax: float) -> float:
        """Calculate solidarity surcharge (Solidaritätszuschlag)."""
        # 5.5% of income tax, but with exemption threshold
        if income_tax <= 972:  # 2024 exemption threshold for single filers
            return 0
        elif income_tax <= 1340:
            # Gradual phase-in zone
            return (income_tax - 972) * 0.2 * 0.055
        else:
            return income_tax * 0.055
    
    def calculate_social_security(self, income: float, age: int) -> Dict[str, float]:
        """Calculate social security contributions."""
        # Simplified calculation - actual rates vary by state and insurance
        pension_rate = 0.093  # Employee portion
        unemployment_rate = 0.012
        health_rate = 0.073
        nursing_rate = 0.01525 if age >= 23 else 0.01275  # Higher rate for childless over 23
        
        # Contribution ceiling (Beitragsbemessungsgrenze)
        pension_ceiling = 87600  # 2024 West Germany
        health_ceiling = 62100   # 2024
        
        pension_base = min(income, pension_ceiling)
        health_base = min(income, health_ceiling)
        
        return {
            "pension": pension_base * pension_rate,
            "unemployment": pension_base * unemployment_rate,
            "health": health_base * health_rate,
            "nursing": health_base * nursing_rate,
            "total": (pension_base * (pension_rate + unemployment_rate) + 
                     health_base * (health_rate + nursing_rate))
        }
    
    def calculate_marginal_rate(self, taxable_income: float) -> float:
        """Calculate marginal tax rate for given income level."""
        for bracket in self.TAX_BRACKETS:
            if bracket["min"] <= taxable_income < bracket["max"]:
                return bracket["rate"]
        return self.TAX_BRACKETS[-1]["rate"]  # Top bracket
    
    def create_fallback_calculation(self, income: float, filing_status: str, dependents: int) -> Dict[str, Any]:
        """Create a simple fallback calculation if detailed calculation fails."""
        basic_allowance = self.get_basic_allowance(filing_status)
        taxable_income = max(0, income - basic_allowance)
        estimated_tax = taxable_income * 0.25  # Rough estimate
        
        return {
            "gross_income": income,
            "filing_status": filing_status,
            "dependents": dependents,
            "basic_allowance": basic_allowance,
            "taxable_income": taxable_income,
            "income_tax": estimated_tax * 0.8,
            "social_security": {"total": estimated_tax * 0.2},
            "total_tax_burden": estimated_tax,
            "net_income": income - estimated_tax,
            "effective_tax_rate": (estimated_tax / income * 100) if income > 0 else 0,
            "error": "Fallback calculation used"
        }
