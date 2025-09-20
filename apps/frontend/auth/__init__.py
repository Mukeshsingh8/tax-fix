"""Authentication for TaxFix Frontend."""

import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from auth_manager import AuthManager

__all__ = ["AuthManager"]
