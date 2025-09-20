"""Navigation component for TaxFix Frontend."""

import streamlit as st
from streamlit_option_menu import option_menu
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from utils.styles import get_navigation_styles


def render_navigation() -> str:
    """Render the main navigation menu and return selected tab."""
    # Handle tab switching - always show navigation but with correct selection
    tab_map = {"Chat": 0, "Dashboard": 1, "Profile": 2}
    
    # Determine which tab should be selected
    if st.session_state.get('switch_to_chat', False):
        forced_index = 0  # Chat
        st.session_state.switch_to_chat = False
        st.session_state.nav_key = st.session_state.get('nav_key', 0) + 1
    elif st.session_state.get('switch_to_dashboard', False):
        forced_index = 1  # Dashboard
        st.session_state.switch_to_dashboard = False
        st.session_state.nav_key = st.session_state.get('nav_key', 0) + 1
    else:
        # Use current tab or default to Chat
        forced_index = tab_map.get(st.session_state.get('current_tab', 'Chat'), 0)
    
    # Always render the navigation menu
    selected = option_menu(
        menu_title=None,
        options=["Chat", "Dashboard", "Profile"],
        icons=["chat-dots", "bar-chart", "person"],
        menu_icon="cast",
        default_index=forced_index,
        orientation="horizontal",
        key=f"main_nav_{st.session_state.get('nav_key', 0)}",
        styles=get_navigation_styles()
    )
    
    # Store current tab
    st.session_state.current_tab = selected
    
    return selected
