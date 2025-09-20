"""
Utility functions for the TaxFix system.
"""

from .data_conversion import (
    to_dict, val_to_str, format_currency, 
    model_to_json, json_to_dict, utc_now_iso
)
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
from .expense_extraction import extract_expense_from_text
from .error_handling import safe_agent_method, safe_execute, create_error_response
from .guidance_generation import (
    create_tax_guidance_prompt,
    create_suggested_actions,
    create_guidance_metadata,
)
# Agent routing functionality moved directly to orchestrator

__all__ = [
    "to_dict",
    "val_to_str", 
    "format_currency",
    "model_to_json",
    "json_to_dict", 
    "utc_now_iso",
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
    "extract_expense_from_text",
    "safe_agent_method",
    "safe_execute",
    "create_error_response",
    "create_tax_guidance_prompt",
    "create_suggested_actions", 
    "create_guidance_metadata",
]