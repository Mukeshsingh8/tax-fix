"""Header component for TaxFix Frontend."""

import streamlit as st


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>🎯 TaxFix AI Assistant</h1>
        <p>Your intelligent German tax advisor powered by AI</p>
    </div>
    """, unsafe_allow_html=True)
