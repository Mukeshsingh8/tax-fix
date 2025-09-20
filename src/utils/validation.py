"""
Validation utilities for the TaxFix system.
"""

from typing import Dict, Any


def clean_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and validate update dictionaries by removing None/empty values.
    
    Args:
        updates: Dictionary of updates to clean
        
    Returns:
        Cleaned dictionary with None/empty values removed
    """
    cleaned = {}
    
    for key, value in updates.items():
        # Skip None values
        if value is None:
            continue
            
        # Skip empty strings
        if isinstance(value, str) and not value.strip():
            continue
            
        # Skip empty collections
        if isinstance(value, (list, dict, set, tuple)) and not value:
            continue
            
        cleaned[key] = value
    
    return cleaned
