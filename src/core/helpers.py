"""
Utility helper functions for the TaxFix system.
"""
import re
import uuid
from typing import List, Optional, Union


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def extract_numbers(text: str) -> List[float]:
    """Extract numbers from text."""
    pattern = r'\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]


def parse_boolean(text: str) -> Optional[bool]:
    """Parse boolean from text."""
    text_lower = text.lower().strip()
    if text_lower in ['true', 'yes', '1', 'on', 'enabled']:
        return True
    elif text_lower in ['false', 'no', '0', 'off', 'disabled']:
        return False
    return None


def parse_tax_year(text: str) -> Optional[int]:
    """Parse tax year from text."""
    # Look for 4-digit years
    pattern = r'\b(20\d{2})\b'
    matches = re.findall(pattern, text)
    if matches:
        year = int(matches[0])
        if 2020 <= year <= 2030:  # Reasonable range
            return year
    return None


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?€$%-]', '', text)
    
    return text


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format currency amount."""
    if currency.upper() == "EUR":
        return f"€{amount:,.2f}"
    elif currency.upper() == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
