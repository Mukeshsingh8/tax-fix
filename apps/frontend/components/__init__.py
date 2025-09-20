"""UI Components for TaxFix Frontend."""

# Import individual component functions
def render_header():
    from .header import render_header as _render_header
    return _render_header()

def render_auth_page(auth_manager):
    from .auth import render_auth_page as _render_auth_page
    return _render_auth_page(auth_manager)

def render_sidebar(auth_manager, api_client):
    from .sidebar import render_sidebar as _render_sidebar
    return _render_sidebar(auth_manager, api_client)

def render_chat_interface(api_client, auth_manager):
    from .chat import render_chat_interface as _render_chat_interface
    return _render_chat_interface(api_client, auth_manager)

def render_dashboard(api_client, auth_manager):
    from .dashboard import render_dashboard as _render_dashboard
    return _render_dashboard(api_client, auth_manager)

def render_profile_page(api_client, auth_manager):
    from .profile import render_profile_page as _render_profile_page
    return _render_profile_page(api_client, auth_manager)

def render_profile_creation_page(api_client, auth_manager):
    from .profile import render_profile_creation_page as _render_profile_creation_page
    return _render_profile_creation_page(api_client, auth_manager)

def render_navigation():
    from .navigation import render_navigation as _render_navigation
    return _render_navigation()

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
