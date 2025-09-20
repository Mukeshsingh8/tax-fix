"""
Utility functions for the TaxFix system.
"""

from .data_conversion import to_dict, val_to_str, format_currency
from .text_processing import role_to_str, clean_text, safe_text, clean_title
from .validation import clean_updates
from .profile_normalization import (
    normalize_employment_status,
    normalize_filing_status,
    normalize_risk_tolerance,
    normalize_tax_goals,
    safe_float,
    safe_int,
)
from .tax_formatting import (
    format_deductions_section,
    format_tax_calculation_section,
    format_insurance_details,
    format_deduction_savings,
)

__all__ = [
    "to_dict",
    "val_to_str", 
    "format_currency",
    "role_to_str",
    "clean_text",
    "safe_text",
    "clean_title",
    "clean_updates",
    "normalize_employment_status",
    "normalize_filing_status", 
    "normalize_risk_tolerance",
    "normalize_tax_goals",
    "safe_float",
    "safe_int",
    "format_deductions_section",
    "format_tax_calculation_section",
    "format_insurance_details",
    "format_deduction_savings",
]
