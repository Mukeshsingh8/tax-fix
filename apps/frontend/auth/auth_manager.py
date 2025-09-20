"""Authentication management for TaxFix Frontend."""

import streamlit as st
import json
import time
import streamlit.components.v1 as components
from typing import Dict, Optional
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from services.api_client import APIClient
from config import STORAGE_KEYS


class AuthManager:
    """Manages user authentication and session persistence."""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def init_session_state(self):
        """Initialize session state variables with persistence support."""
        # Initialize defaults first
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
        if 'current_session_id' not in st.session_state:
            st.session_state.current_session_id = None
        if 'user_profile' not in st.session_state:
            st.session_state.user_profile = None
        
        # Try to restore session from URL parameters (for refresh handling)
        if 'auth_restore_attempted' not in st.session_state:
            st.session_state.auth_restore_attempted = True
            self.check_url_auth_restore()
    
    def check_url_auth_restore(self):
        """Check URL parameters for auth restoration after refresh."""
        try:
            # Simple approach: check URL for auth restoration
            query_params = st.query_params
            if query_params.get('auth_token') and query_params.get('user_id'):
                token = query_params['auth_token']
                user_id = query_params['user_id']
                
                # Validate token with backend using existing /auth/me endpoint
                validation_response = self.api_client.validate_token(token)
                if validation_response.get("success"):
                    user_data = validation_response.get("user")
                    # Check both possible user ID field names
                    actual_user_id = user_data.get("id") or user_data.get("user_id") if user_data else None
                    
                    if user_data and actual_user_id == user_id:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.session_state.token = token
                        
                        # Store in browser storage for future refreshes
                        self.store_session_in_storage()
                        
                        # Clean URL
                        st.query_params.clear()
                        st.rerun()
        except Exception as e:
            # If restoration fails, continue normally
            pass
    
    def store_session_in_storage(self):
        """Store authentication session in browser storage."""
        if st.session_state.authenticated and st.session_state.user and st.session_state.token:
            # Escape user data for JavaScript
            user_json = json.dumps(st.session_state.user).replace("'", "\\'")
            token = st.session_state.token
            
            storage_script = f"""
            <script>
            sessionStorage.setItem('{STORAGE_KEYS["auth"]}', 'true');
            sessionStorage.setItem('{STORAGE_KEYS["user"]}', '{user_json}');
            sessionStorage.setItem('{STORAGE_KEYS["token"]}', '{token}');
            </script>
            """
            components.html(storage_script, height=0)
    
    def clear_session_storage(self):
        """Clear authentication session from browser storage."""
        clear_script = f"""
        <script>
        sessionStorage.removeItem('{STORAGE_KEYS["auth"]}');
        sessionStorage.removeItem('{STORAGE_KEYS["user"]}');
        sessionStorage.removeItem('{STORAGE_KEYS["token"]}');
        localStorage.removeItem('{STORAGE_KEYS["auth"]}');
        localStorage.removeItem('{STORAGE_KEYS["user"]}');
        localStorage.removeItem('{STORAGE_KEYS["token"]}');
        </script>
        """
        components.html(clear_script, height=0)
    
    def login(self, email: str, password: str) -> bool:
        """Login user."""
        response = self.api_client.login(email, password)
        
        if "error" not in response and response.get("success"):
            st.session_state.authenticated = True
            st.session_state.user = response.get("user")
            st.session_state.token = response.get("token")
            
            # Store authentication in browser storage for persistence
            self.store_session_in_storage()
            
            # Set URL parameters for refresh persistence (defensive access)
            user_id = None
            if st.session_state.user:
                user_id = st.session_state.user.get("id") or st.session_state.user.get("user_id")
            
            if user_id:
                st.query_params["auth_token"] = st.session_state.token
                st.query_params["user_id"] = user_id
            
            return True
        else:
            st.error(response.get("error", "Login failed"))
            return False
    
    def register(self, name: str, email: str, password: str) -> bool:
        """Register user."""
        response = self.api_client.register(name, email, password)
        
        if "error" not in response and response.get("success"):
            st.success("Registration successful! Please login.")
            return True
        else:
            st.error(response.get("error", "Registration failed"))
            return False
    
    def logout(self):
        """Logout user."""
        if st.session_state.token:
            self.api_client.logout(st.session_state.token)
        
        # Clear session storage
        self.clear_session_storage()
        
        # Clear URL parameters
        st.query_params.clear()
        
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.token = None
        st.session_state.conversation_history = []
        st.session_state.current_session_id = None
        st.session_state.user_profile = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user."""
        return st.session_state.get('user')
    
    def get_token(self) -> Optional[str]:
        """Get current authentication token."""
        return st.session_state.get('token')
