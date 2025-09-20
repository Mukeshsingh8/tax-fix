"""
Refactored TaxFix Frontend - Production-Grade Modular Architecture
"""

import streamlit as st
from config import APP_CONFIG
from utils import apply_global_styles
from services import APIClient
from auth import AuthManager
from components import (
    render_header,
    render_auth_page,
    render_sidebar, 
    render_navigation,
    render_chat_interface,
    render_dashboard,
    render_profile_page,
    render_profile_creation_page
)


class TaxFixApp:
    """Main TaxFix application class - streamlined and modular."""
    
    def __init__(self):
        """Initialize the application."""
        # Configure Streamlit page
        st.set_page_config(**APP_CONFIG)
        
        # Apply global styles
        apply_global_styles()
        
        # Initialize services
        self.api_client = APIClient()
        self.auth_manager = AuthManager(self.api_client)
        
        # Initialize session state
        self.auth_manager.init_session_state()
    
    def run(self):
        """Run the main application."""
        # Render header
        render_header()
        
        # Check authentication
        if not self.auth_manager.is_authenticated():
            render_auth_page(self.auth_manager)
            return
        
        # Check if user has a profile
        if not self._has_user_profile():
            if not self._try_load_profile():
                render_profile_creation_page(self.api_client, self.auth_manager)
                return
        
        # Render main application
        self._render_main_app()
    
    def _has_user_profile(self) -> bool:
        """Check if user has a profile in session state."""
        return st.session_state.get('user_profile') is not None
    
    def _try_load_profile(self) -> bool:
        """Try to load user profile from backend."""
        try:
            response = self.api_client.get_user_profile(self.auth_manager.get_token())
            if response.get("success") and response.get("profile"):
                st.session_state.user_profile = response.get("profile")
                return True
            return False
        except Exception:
            return False
    
    def _render_main_app(self):
        """Render the main authenticated application."""
        # Render navigation and get selected tab
        selected_tab = render_navigation()
        
        # Render sidebar
        render_sidebar(self.auth_manager, self.api_client)
        
        # Render selected page
        if selected_tab == "Chat":
            render_chat_interface(self.api_client, self.auth_manager)
        elif selected_tab == "Dashboard":
            render_dashboard(self.api_client, self.auth_manager)
        elif selected_tab == "Profile":
            render_profile_page(self.api_client, self.auth_manager)


def main():
    """Main entry point for the application."""
    app = TaxFixApp()
    app.run()


if __name__ == "__main__":
    main()
