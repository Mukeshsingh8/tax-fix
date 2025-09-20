"""Tax knowledge base models (enriched, backward-compatible)."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaxCategory(str, Enum):
    """Tax category enumeration."""
    INCOME = "income"
    DEDUCTIONS = "deductions"
    CREDITS = "credits"
    EXPENSES = "expenses"
    INVESTMENTS = "investments"
    BUSINESS = "business"
    PROPERTY = "property"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    RETIREMENT = "retirement"


class DeductionType(str, Enum):
    """Deduction type enumeration."""
    STANDARD = "standard"
    ITEMIZED = "itemized"
    ABOVE_THE_LINE = "above_the_line"
    BUSINESS = "business"
    MEDICAL = "medical"
    CHARITABLE = "charitable"
    EDUCATION = "education"
    HOME_OFFICE = "home_office"
    CREDIT = "credit"


class TaxRule(BaseModel):
    """Tax rule model."""
    id: str = Field(..., description="Unique rule ID")
    title: str = Field(..., description="Rule title")
    description: str = Field(..., description="Detailed rule description")
    category: TaxCategory = Field(..., description="Tax category")
    applicable_conditions: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    year_applicable: int = Field(..., description="Tax year this rule applies to")
    priority: int = Field(default=0, description="Rule priority for matching")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        extra = "ignore"  # tolerate older data with extra keys


class Deduction(BaseModel):
    """Tax deduction model (with typed fields + metadata fallback)."""
    id: str = Field(..., description="Unique deduction ID")
    name: str = Field(..., description="Deduction name")
    description: str = Field(..., description="Deduction description")
    deduction_type: DeductionType = Field(..., description="Type of deduction")
    category: TaxCategory = Field(..., description="Tax category")

    # Core amounts
    max_amount: Optional[float] = None
    percentage: Optional[float] = None

    # Eligibility & docs
    eligibility_criteria: List[str] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)
    common_expenses: List[str] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)

    # Applicability
    year_applicable: int = Field(..., description="Tax year this deduction applies to")
    is_commonly_used: bool = Field(default=False)

    # NEW optional typed fields (nice to have; we also fall back to metadata):
    applicable_filing_status: Optional[List[str]] = None
    income_limit: Optional[float] = None
    rates: Optional[Dict[str, float]] = None          # e.g., {"first_20_km": 0.30, "from_21_km": 0.38}
    per_day_rate: Optional[float] = None              # e.g., 6.0 for home office

    # Always available catch-all
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        extra = "ignore"  # tolerate older data with extra keys

    # ----- Convenience accessors (use typed field, else fall back to metadata) -----
    def get_applicable_filing_status(self) -> List[str]:
        if self.applicable_filing_status:
            return self.applicable_filing_status
        return list(self.metadata.get("applicable_filing_status", []))

    def get_income_limit(self) -> Optional[float]:
        if self.income_limit is not None:
            return self.income_limit
        return self.metadata.get("income_limit")

    def get_rates(self) -> Dict[str, float]:
        if self.rates:
            return self.rates
        return dict(self.metadata.get("rates", {}))

    def get_per_day_rate(self) -> Optional[float]:
        if self.per_day_rate is not None:
            return self.per_day_rate
        return self.metadata.get("per_day_rate")


class TaxCalculation(BaseModel):
    """Generic (jurisdiction-agnostic) tax calculation result (kept for compatibility)."""
    user_id: str = Field(..., description="User ID")
    tax_year: int = Field(..., description="Tax year")
    gross_income: float = Field(..., description="Gross income")
    adjusted_gross_income: float = Field(..., description="Adjusted gross income")
    standard_deduction: float = Field(..., description="Standard deduction amount")
    itemized_deductions: float = Field(default=0.0, description="Itemized deductions")
    taxable_income: float = Field(..., description="Taxable income")
    tax_owed: float = Field(..., description="Tax owed")
    credits: float = Field(default=0.0, description="Tax credits")
    refund_amount: float = Field(..., description="Refund amount")
    deductions_used: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class GermanTaxBreakdown(BaseModel):
    """
    German-specific tax breakdown that matches TaxKnowledgeService.calculate_german_tax().
    Use this for strongly-typed results instead of a raw dict.
    """
    tax_year: int = Field(default=2024)
    gross_income: float

    # Allowances
    basic_allowance: float
    child_allowance: float
    total_allowances: float

    # Social contributions
    health_insurance_contribution: float
    long_term_care_contribution: float
    total_social_contributions: float

    # Tax base and taxes
    taxable_income: float
    income_tax: float
    solidarity_surcharge: float
    church_tax: float
    total_tax: float

    # Summary metrics
    total_deductions: float
    effective_tax_rate: float         # percent
    total_effective_rate: float       # percent
    net_income: float

    # Details
    health_insurance_details: Dict[str, Any] = Field(default_factory=dict)
    long_term_care_details: Dict[str, Any] = Field(default_factory=dict)

    generated_at: datetime = Field(default_factory=datetime.utcnow)
