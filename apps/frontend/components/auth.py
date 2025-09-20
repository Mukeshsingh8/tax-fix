"""Authentication components for TaxFix Frontend."""

import streamlit as st
from ..auth.auth_manager import AuthManager
from ..utils.helpers import ValidationHelper


def render_auth_page(auth_manager: AuthManager):
    """Render authentication page with login and registration."""
    st.markdown("""
    <div class="welcome-message">
        <h4>👋 Welcome to TaxFix AI!</h4>
        <p>Ask me anything about German taxes, deductions, or tax planning strategies.</p>
        <p style="font-size: 0.9em; margin-top: 1rem;">
            💡 <strong>Try asking:</strong> "What deductions can I claim?" or "How much tax will I pay?"
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        render_login_form(auth_manager)
    
    with tab2:
        render_registration_form(auth_manager)


def render_login_form(auth_manager: AuthManager):
    """Render login form."""
    st.header("Login to Your Account")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Login", use_container_width=True)
        
        if submit_button:
            if email and password:
                if auth_manager.login(email, password):
                    st.rerun()
            else:
                st.error("Please fill in all fields")


def render_registration_form(auth_manager: AuthManager):
    """Render registration form."""
    st.header("Create New Account")
    
    with st.form("registration_form"):
        name = st.text_input("Full Name", placeholder="Enter your full name")
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        submit_button = st.form_submit_button("Register", use_container_width=True)
        
        if submit_button:
            if name and email and password and confirm_password:
                # Validate email format
                if not ValidationHelper.validate_email(email):
                    st.error("Please enter a valid email address")
                    return
                
                # Validate password strength
                is_valid, message = ValidationHelper.validate_password(password)
                if not is_valid:
                    st.error(message)
                    return
                
                # Check password confirmation
                if password != confirm_password:
                    st.error("Passwords do not match")
                    return
                
                # Attempt registration
                if auth_manager.register(name, email, password):
                    st.success("Registration successful! Please login with your credentials.")
            else:
                st.error("Please fill in all fields")
