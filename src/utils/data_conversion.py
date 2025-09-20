"""
Data conversion utilities for the TaxFix system.
"""

from typing import Dict, Any, Optional


def to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert pydantic model or object to dict safely.
    
    Handles various types of objects including Pydantic models,
    dataclasses, and regular objects with attributes.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    
    # Try Pydantic methods first
    for fn_name in ("model_dump", "dict"):
        fn = getattr(obj, fn_name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    
    # Fallback: best-effort attribute mapping
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}
    except Exception:
        return {}


def val_to_str(enum_or_str: Any) -> Optional[str]:
    """
    Return string value from enum or plain str.
    
    Handles enum types that have a .value attribute as well as plain strings.
    """
    if enum_or_str is None:
        return None
    return getattr(enum_or_str, "value", enum_or_str)


def format_currency(amount: Optional[float]) -> str:
    """
    Format amount as Euro currency string.
    
    Args:
        amount: The amount to format, can be None
        
    Returns:
        Formatted currency string (e.g., "€1,234.56")
    """
    try:
        return f"€{float(amount):,.2f}"
    except (TypeError, ValueError):
        return "€0.00"
