"""
Profile data normalization utilities.
"""

from typing import Dict, Any, List, Optional


def normalize_employment_status(value: Any) -> Optional[str]:
    """Normalize employment status to standard values."""
    if not value:
        return None
        
    emp = str(value).strip().lower()
    emp_map = {
        "employed": "employed",
        "employee": "employed",
        "self-employed": "self_employed",
        "self employed": "self_employed",
        "freelancer": "self_employed",
        "unemployed": "unemployed",
        "retired": "retired",
        "student": "student",
    }
    return emp_map.get(emp, emp) if emp else None


def normalize_filing_status(value: Any) -> Optional[str]:
    """Normalize filing status to standard values."""
    if not value:
        return None
        
    fil = str(value).strip().lower().replace(" ", "_")
    fil_map = {
        "single": "single",
        "married_joint": "married_joint",
        "married_separate": "married_separate",
        "head_of_household": "head_of_household",
        "qualifying_widow": "qualifying_widow",
        "married": "married_joint",  # default if ambiguous
    }
    return fil_map.get(fil, fil) if fil else None


def normalize_risk_tolerance(value: Any) -> Optional[str]:
    """Normalize risk tolerance to standard values."""
    if not value:
        return None
        
    risk = str(value).strip().lower()
    risk_map = {
        "low": "conservative",
        "medium": "moderate",
        "mid": "moderate",
        "moderate": "moderate",
        "high": "aggressive",
        "aggressive": "aggressive",
        "conservative": "conservative",
    }
    return risk_map.get(risk, risk) if risk else None


def normalize_tax_goals(value: Any) -> List[str]:
    """Normalize tax goals list."""
    if not value:
        return []
        
    if not isinstance(value, list):
        return []
        
    cleaned = []
    for goal in value:
        goal_str = str(goal).strip().lower().replace(" ", "_")
        if goal_str:
            cleaned.append(goal_str)
    return cleaned


def safe_float(value: Any, minimum: float = 0.0) -> Optional[float]:
    """Safely convert value to float with minimum constraint."""
    if value is None:
        return None
    try:
        return max(minimum, float(value))
    except (ValueError, TypeError):
        return None


def safe_int(value: Any, minimum: int = 0) -> Optional[int]:
    """Safely convert value to int with minimum constraint."""
    if value is None:
        return None
    try:
        return max(minimum, int(value))
    except (ValueError, TypeError):
        return None
