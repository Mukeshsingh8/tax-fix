"""Configuration settings for TaxFix Frontend."""

import os
from typing import Dict, Any

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# App Configuration
APP_CONFIG = {
    "page_title": "TaxFix - AI Tax Advisor",
    "page_icon": "💰",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# UI Theme Configuration
THEME_CONFIG = {
    "primary_color": "#667eea",
    "secondary_color": "#764ba2",
    "accent_color": "#4facfe",
    "success_color": "#00f2fe",
    "error_color": "#ff6b6b",
    "warning_color": "#fa709a"
}

# Session Storage Keys
STORAGE_KEYS = {
    "auth": "taxfix_auth",
    "user": "taxfix_user", 
    "token": "taxfix_token"
}

# Default Values
DEFAULTS = {
    "employment_status": "Not specified",
    "filing_status": "Not specified",
    "dependents": 0,
    "risk_tolerance": "Conservative"
}
