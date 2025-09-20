"""
Text processing utilities for the TaxFix system.
"""

import re
from typing import Any


def role_to_str(role: Any) -> str:
    """
    Normalize a role that might be an enum or string.
    
    Args:
        role: Role object that may have a .value attribute or be a string
        
    Returns:
        String representation of the role
    """
    try:
        return getattr(role, "value", role) or ""
    except Exception:
        return str(role or "")


def clean_text(text: str, max_length: int = 1000) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Text to clean
        max_length: Maximum length to truncate to
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Truncate if needed
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "..."
    
    return cleaned


def safe_text(s: Any, max_len: int = 2000) -> str:
    """
    Basic text sanitizer with length guard.
    
    Args:
        s: Input that should be converted to safe text
        max_len: Maximum length allowed
        
    Returns:
        Safe, length-limited text
    """
    if s is None:
        return ""
    
    try:
        text = str(s).strip()
        # Remove any potential harmful characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        if len(text) > max_len:
            text = text[:max_len].rstrip() + "..."
        
        return text
    except Exception:
        return ""


def clean_title(s: str, max_len: int = 50) -> str:
    """
    Trim, strip quotes/newlines, enforce max length for titles.
    
    Args:
        s: Title string to clean
        max_len: Maximum length for the title
        
    Returns:
        Cleaned title string
    """
    if not s:
        return ""
    
    # Remove quotes and clean whitespace
    cleaned = s.strip('\'"').replace('\n', ' ').replace('\r', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Truncate if needed
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip() + "..."
    
    return cleaned
