"""Dashboard component for TaxFix Frontend."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from services.api_client import APIClient
from auth.auth_manager import AuthManager
from utils.helpers import DataFormatter
from config import DEFAULTS


def render_dashboard(api_client: APIClient, auth_manager: AuthManager):
    """Render the main dashboard."""
    st.markdown("## 📊 Tax Dashboard")
    
    # Get dashboard data
    dashboard_data = get_dashboard_data(api_client, auth_manager.get_token())
    
    if not dashboard_data:
        st.error("Unable to load dashboard data")
        return
    
    # Render dashboard sections
    render_profile_overview(dashboard_data.get("profile", {}))
    render_tax_summary(dashboard_data.get("tax_calculations", {}))
    render_expense_tracking(dashboard_data.get("expenses", {}))
    render_tax_breakdown_analysis(dashboard_data)
    render_smart_tax_optimization(dashboard_data)
    render_quick_actions()


def get_dashboard_data(api_client: APIClient, token: str) -> Dict[str, Any]:
    """Get comprehensive dashboard data."""
    try:
        response = api_client.get_dashboard_data(token)
        if response.get("success"):
            return response
        else:
            st.error(f"Error loading dashboard: {response.get('error', 'Unknown error')}")
            return {}
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return {}


def render_profile_overview(profile_data: Dict[str, Any]):
    """Render profile overview section."""
    st.markdown('<div class="section-header">👤 Profile Overview</div>', unsafe_allow_html=True)
    
    # Get profile values with defaults
    employment_status = profile_data.get("employment_status", DEFAULTS["employment_status"])
    filing_status = profile_data.get("filing_status", DEFAULTS["filing_status"])
    dependents = profile_data.get("dependents", DEFAULTS["dependents"])
    risk_tolerance = profile_data.get("risk_tolerance", DEFAULTS["risk_tolerance"])
    
    # Create profile cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        icon = DataFormatter.get_icon_for_status(employment_status)
        st.markdown(f"""
        <div class="profile-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">Employment</div>
            <div class="metric-value">{employment_status.replace('_', ' ').title()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="profile-card">
            <div class="metric-icon">📋</div>
            <div class="metric-label">Filing Status</div>
            <div class="metric-value">{filing_status.replace('_', ' ').title()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        dependents_icon = DataFormatter.get_dependents_icon(dependents)
        st.markdown(f"""
        <div class="profile-card">
            <div class="metric-icon">{dependents_icon}</div>
            <div class="metric-label">Dependents</div>
            <div class="metric-value">{dependents}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        risk_icon = DataFormatter.get_icon_for_risk(risk_tolerance)
        st.markdown(f"""
        <div class="profile-card">
            <div class="metric-icon">{risk_icon}</div>
            <div class="metric-label">Risk Level</div>
            <div class="metric-value">{risk_tolerance.title()}</div>
        </div>
        """, unsafe_allow_html=True)


def render_tax_summary(tax_data: Dict[str, Any]):
    """Render tax summary section."""
    st.markdown('<div class="section-header">💰 Tax Summary</div>', unsafe_allow_html=True)
    
    if not tax_data:
        st.info("Complete your profile to see tax calculations")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gross_income = tax_data.get("annual_income", 0)
        st.markdown(f"""
        <div class="tax-card">
            <div class="metric-icon">💵</div>
            <div class="metric-label">Gross Income</div>
            <div class="metric-value">{DataFormatter.format_currency(gross_income)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        taxable_income = tax_data.get("taxable_income", 0)
        st.markdown(f"""
        <div class="tax-card">
            <div class="metric-icon">📊</div>
            <div class="metric-label">Taxable Income</div>
            <div class="metric-value">{DataFormatter.format_currency(taxable_income)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        income_tax = tax_data.get("income_tax", 0)
        st.markdown(f"""
        <div class="tax-card">
            <div class="metric-icon">💸</div>
            <div class="metric-label">Income Tax</div>
            <div class="metric-value">{DataFormatter.format_currency(income_tax)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_tax = tax_data.get("total_tax", 0)
        st.markdown(f"""
        <div class="tax-card">
            <div class="metric-icon">🧾</div>
            <div class="metric-label">Total Tax</div>
            <div class="metric-value">{DataFormatter.format_currency(total_tax)}</div>
        </div>
        """, unsafe_allow_html=True)


def render_expense_tracking(expense_data: Dict[str, Any]):
    """Render expense tracking section."""
    st.markdown('<div class="section-header">💳 Expense Tracking</div>', unsafe_allow_html=True)
    
    summary = expense_data.get("summary", {})
    items = expense_data.get("items", [])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_count = summary.get("total_count", 0)
        st.markdown(f"""
        <div class="expense-card">
            <div class="metric-icon">📝</div>
            <div class="metric-label">Total Expenses</div>
            <div class="metric-value">{total_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_amount = summary.get("total_amount", 0)
        st.markdown(f"""
        <div class="expense-card">
            <div class="metric-icon">💰</div>
            <div class="metric-label">Total Amount</div>
            <div class="metric-value">{DataFormatter.format_currency(total_amount)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_amount = summary.get("average_amount", 0)
        st.markdown(f"""
        <div class="expense-card">
            <div class="metric-icon">📊</div>
            <div class="metric-label">Average Expense</div>
            <div class="metric-value">{DataFormatter.format_currency(avg_amount)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        tax_savings = total_amount * 0.3  # Estimated 30% tax savings
        st.markdown(f"""
        <div class="expense-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-label">Est. Tax Savings</div>
            <div class="metric-value">{DataFormatter.format_currency(tax_savings)}</div>
        </div>
        """, unsafe_allow_html=True)


def render_tax_breakdown_analysis(dashboard_data: Dict[str, Any]):
    """Render tax breakdown analysis with charts."""
    st.markdown('<div class="section-header">📈 Tax Breakdown Analysis</div>', unsafe_allow_html=True)
    
    tax_data = dashboard_data.get("tax_calculations", {})
    expense_data = dashboard_data.get("expenses", {})
    
    if not tax_data:
        st.info("Complete your profile to see tax analysis")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Tax breakdown pie chart
        st.subheader("Tax Components")
        
        income_tax = tax_data.get("income_tax", 0)
        solidarity_surcharge = tax_data.get("solidarity_surcharge", 0)
        church_tax = tax_data.get("church_tax", 0)
        
        if income_tax > 0:
            tax_breakdown = pd.DataFrame({
                'Component': ['Income Tax', 'Solidarity Surcharge', 'Church Tax'],
                'Amount': [income_tax, solidarity_surcharge, church_tax]
            })
            
            fig = px.pie(tax_breakdown, values='Amount', names='Component',
                        title="Tax Components Breakdown")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tax data available")
    
    with col2:
        # Expense categories chart
        st.subheader("Expense Categories")
        
        items = expense_data.get("items", [])
        if items:
            # Group expenses by category
            category_totals = {}
            for item in items:
                category = item.get("category", "Other")
                amount = item.get("amount", 0)
                category_totals[category] = category_totals.get(category, 0) + amount
            
            if category_totals:
                expense_df = pd.DataFrame(
                    list(category_totals.items()),
                    columns=['Category', 'Amount']
                )
                
                fig = px.bar(expense_df, x='Category', y='Amount',
                           title="Expenses by Category")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expense categories to display")
        else:
            st.info("No expenses recorded yet")


def render_smart_tax_optimization(dashboard_data: Dict[str, Any]):
    """Render smart tax optimization suggestions."""
    st.markdown('<div class="section-header">🎯 Smart Tax Optimization</div>', unsafe_allow_html=True)
    
    tax_data = dashboard_data.get("tax_calculations", {})
    profile_data = dashboard_data.get("profile", {})
    
    suggestions = generate_tax_suggestions(tax_data, profile_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💡 Optimization Opportunities")
        for suggestion in suggestions:
            st.markdown(f"• {suggestion}")
    
    with col2:
        st.subheader("📊 Tax Rate Analysis")
        
        if tax_data:
            effective_rate = tax_data.get("effective_tax_rate", 0)
            
            # Create gauge chart for tax rate
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = effective_rate,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Effective Tax Rate"},
                gauge = {
                    'axis': {'range': [None, 50]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 20], 'color': "lightgray"},
                        {'range': [20, 35], 'color': "gray"},
                        {'range': [35, 50], 'color': "lightcoral"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 42
                    }
                }
            ))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Complete your profile for tax rate analysis")


def generate_tax_suggestions(tax_data: Dict[str, Any], profile_data: Dict[str, Any]) -> list:
    """Generate personalized tax optimization suggestions."""
    suggestions = []
    
    # Basic suggestions
    suggestions.append("Consider maximizing your Riester pension contributions")
    suggestions.append("Track home office expenses if you work from home")
    suggestions.append("Save receipts for professional development courses")
    
    # Income-based suggestions
    annual_income = tax_data.get("annual_income", 0)
    if annual_income > 60000:
        suggestions.append("Consider additional voluntary pension contributions")
        suggestions.append("Explore tax-efficient investment options")
    
    # Employment-based suggestions
    employment_status = profile_data.get("employment_status", "")
    if employment_status == "self_employed":
        suggestions.append("Maximize business expense deductions")
        suggestions.append("Consider professional liability insurance deductions")
    
    return suggestions


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown('<div class="section-header">⚡ Quick Actions</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💬 Ask Tax Question", use_container_width=True):
            st.session_state.prefill_message = "I have a tax question about "
            st.session_state.switch_to_chat = True
            st.rerun()
    
    with col2:
        if st.button("📝 Add Expense", use_container_width=True):
            st.session_state.prefill_message = "I want to add a new expense: "
            st.session_state.switch_to_chat = True
            st.rerun()
    
    with col3:
        if st.button("📊 Tax Calculation", use_container_width=True):
            st.session_state.prefill_message = "Can you calculate my taxes based on "
            st.session_state.switch_to_chat = True
            st.rerun()
    
    with col4:
        if st.button("🎯 Optimization Tips", use_container_width=True):
            st.session_state.prefill_message = "What tax optimization strategies do you recommend for "
            st.session_state.switch_to_chat = True
            st.rerun()
