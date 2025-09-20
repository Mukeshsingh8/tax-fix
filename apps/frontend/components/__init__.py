"""UI Components for TaxFix Frontend."""

from .header import render_header
from .auth import render_auth_page
from .sidebar import render_sidebar
from .chat import render_chat_interface
from .dashboard import render_dashboard
from .profile import render_profile_page, render_profile_creation_page
from .navigation import render_navigation

__all__ = [
    "render_header",
    "render_auth_page", 
    "render_sidebar",
    "render_chat_interface",
    "render_dashboard",
    "render_profile_page",
    "render_profile_creation_page",
    "render_navigation"
]
