"""Profile component for TaxFix Frontend."""

import streamlit as st
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from services.api_client import APIClient
from auth.auth_manager import AuthManager


def render_profile_page(api_client: APIClient, auth_manager: AuthManager):
    """Render the profile management page."""
    st.markdown("## ⚙️ Profile Management")
    
    # Get current user and profile
    user = auth_manager.get_current_user()
    profile_response = api_client.get_user_profile(auth_manager.get_token())
    
    current_profile = {}
    if profile_response.get("success"):
        current_profile = profile_response.get("profile", {})
    
    render_profile_form(api_client, auth_manager, user, current_profile)


def render_profile_creation_page(api_client: APIClient, auth_manager: AuthManager):
    """Render the profile creation page for new users."""
    st.markdown("## 🎉 Welcome to TaxFix!")
    st.markdown("Let's set up your tax profile to provide personalized advice.")
    
    user = auth_manager.get_current_user()
    render_profile_form(api_client, auth_manager, user, {}, is_creation=True)


def render_profile_form(api_client: APIClient, auth_manager: AuthManager, user: Dict, profile: Dict, is_creation: bool = False):
    """Render the profile form."""
    
    # User info header
    if user:
        st.markdown(f"""
        <div class="profile-card" style="margin-bottom: 2rem;">
            <div class="metric-icon">👤</div>
            <h3>{user.get('name', 'User')}</h3>
            <p>{user.get('email', 'No email')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.form("profile_form"):
        st.markdown("### 📋 Personal Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Auto-populate name from user data
            name = st.text_input(
                "Full Name", 
                value=user.get('name', '') if user else '',
                disabled=True,  # Make it read-only since it comes from user account
                help="This is your account name and cannot be changed here"
            )
            
            annual_income = st.number_input(
                "Annual Income (€)", 
                min_value=0.0, 
                value=float(profile.get("annual_income", 0)),
                step=1000.0,
                help="Your gross annual income in euros"
            )
        
        with col2:
            # Auto-populate email from user data  
            email = st.text_input(
                "Email Address",
                value=user.get('email', '') if user else '',
                disabled=True,  # Make it read-only since it comes from user account
                help="This is your account email and cannot be changed here"
            )
            
            dependents = st.number_input(
                "Number of Dependents", 
                min_value=0, 
                max_value=10, 
                value=profile.get("dependents", 0),
                help="Number of children or other dependents"
            )
        
        st.markdown("---")
        st.markdown("### 💼 Financial Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            employment_status = st.selectbox(
                "Employment Status",
                options=["employed", "self_employed", "unemployed", "retired", "student"],
                index=get_index_for_value(
                    ["employed", "self_employed", "unemployed", "retired", "student"],
                    profile.get("employment_status", "employed")
                ),
                help="Your current employment situation"
            )
            
            risk_tolerance = st.selectbox(
                "Risk Tolerance",
                options=["conservative", "moderate", "aggressive"],
                index=get_index_for_value(
                    ["conservative", "moderate", "aggressive"],
                    profile.get("risk_tolerance", "conservative")
                ),
                help="Your comfort level with financial risk"
            )
        
        with col2:
            filing_status = st.selectbox(
                "Filing Status",
                options=["single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"],
                index=get_index_for_value(
                    ["single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"],
                    profile.get("filing_status", "single")
                ),
                help="Your tax filing status"
            )
            
            preferred_communication_style = st.selectbox(
                "Communication Style",
                options=["friendly", "professional", "detailed", "concise"],
                index=get_index_for_value(
                    ["friendly", "professional", "detailed", "concise"],
                    profile.get("preferred_communication_style", "friendly")
                ),
                help="How you prefer to receive advice"
            )
        
        st.markdown("---")
        st.markdown("### 🎯 Tax Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            tax_complexity_level = st.selectbox(
                "Tax Knowledge Level",
                options=["beginner", "intermediate", "advanced"],
                index=get_index_for_value(
                    ["beginner", "intermediate", "advanced"],
                    profile.get("tax_complexity_level", "beginner")
                ),
                help="Your familiarity with tax concepts"
            )
        
        with col2:
            preferred_deductions = st.multiselect(
                "Interested Deductions",
                options=[
                    "Home Office", "Professional Development", "Travel Expenses", 
                    "Equipment & Tools", "Insurance", "Charitable Donations",
                    "Retirement Contributions", "Health Expenses"
                ],
                default=profile.get("preferred_deductions", []),
                help="Types of deductions you're interested in"
            )
        
        st.markdown("---")
        st.markdown("### 🎯 Tax Goals")
        
        # Visual tax goals selector
        st.markdown("Select your primary tax goals:")
        
        goal_options = [
            ("💰 Minimize Tax Liability", "minimize_taxes"),
            ("📈 Maximize Deductions", "maximize_deductions"), 
            ("🏠 Plan for Major Purchase", "major_purchase"),
            ("🎓 Education Planning", "education_planning"),
            ("🏖️ Retirement Planning", "retirement_planning"),
            ("💼 Business Growth", "business_growth")
        ]
        
        current_goals = profile.get("tax_goals", [])
        selected_goals = []
        
        cols = st.columns(3)
        for i, (display_name, goal_value) in enumerate(goal_options):
            with cols[i % 3]:
                if st.checkbox(display_name, value=goal_value in current_goals, key=f"goal_{goal_value}"):
                    selected_goals.append(goal_value)
        
        st.markdown("---")
        
        # Submit button
        submit_button = st.form_submit_button(
            "Create Profile" if is_creation else "Update Profile",
            use_container_width=True
        )
        
        if submit_button:
            # Prepare profile data
            profile_data = {
                "annual_income": annual_income,
                "employment_status": employment_status,
                "filing_status": filing_status,
                "dependents": dependents,
                "tax_goals": selected_goals,
                "risk_tolerance": risk_tolerance,
                "preferred_deductions": preferred_deductions,
                "preferred_communication_style": preferred_communication_style,
                "tax_complexity_level": tax_complexity_level
            }
            
            # Submit profile
            if handle_profile_submission(api_client, auth_manager, profile_data, is_creation):
                if is_creation:
                    st.success("Profile created successfully! Welcome to TaxFix!")
                    st.session_state.user_profile = profile_data
                    st.rerun()
                else:
                    st.success("Profile updated successfully!")
                    st.session_state.user_profile = profile_data


def handle_profile_submission(api_client: APIClient, auth_manager: AuthManager, profile_data: Dict, is_creation: bool) -> bool:
    """Handle profile form submission."""
    try:
        token = auth_manager.get_token()
        
        if is_creation:
            response = api_client.create_user_profile(profile_data, token)
        else:
            response = api_client.update_user_profile(profile_data, token)
        
        if response.get("success"):
            return True
        else:
            st.error(f"Error saving profile: {response.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        st.error(f"Error connecting to server: {str(e)}")
        return False


def get_index_for_value(options: List[str], value: str) -> int:
    """Get index of value in options list, defaulting to 0."""
    try:
        return options.index(value)
    except (ValueError, AttributeError):
        return 0
