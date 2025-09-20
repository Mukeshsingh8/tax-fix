"""
Data conversion utilities for the TaxFix system.
Consolidates all data conversion patterns from across services.
"""

import json
from typing import Dict, Any, Optional
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone


def to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert pydantic model, dataclass, or object to dict safely.
    
    Handles various types of objects including Pydantic models (v1/v2),
    dataclasses, and regular objects with attributes.
    
    This consolidates the _to_dict patterns from tax_knowledge_service.py
    and other services.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    
    # Try Pydantic v1/v2 methods first
    for fn_name in ("dict", "model_dump"):
        fn = getattr(obj, fn_name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    
    # Try dataclass conversion
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass
    
    # Fallback: best-effort attribute mapping
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}
    except Exception:
        return {}


def model_to_json(obj: Any) -> str:
    """
    Serialize pydantic v1/v2 models safely; fallback to json.dumps.
    
    This consolidates the _model_to_json pattern from memory.py
    """
    # Try Pydantic serialization methods
    for fn in ("model_dump_json", "json"):
        f = getattr(obj, fn, None)
        if callable(f):
            try:
                return f()
            except Exception:
                pass
    
    # Fallback to standard JSON serialization
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return "{}"


def json_to_dict(s: Optional[str]) -> Dict[str, Any]:
    """
    Parse JSON string to dict safely.
    
    This consolidates the _json_to_dict pattern from memory.py
    """
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def utc_now_iso() -> str:
    """
    Get current UTC timestamp as ISO string.
    
    This consolidates the _utc_now_iso pattern from memory.py
    """
    return datetime.now(timezone.utc).isoformat()


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
