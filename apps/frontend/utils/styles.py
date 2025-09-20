"""CSS styles and styling utilities for TaxFix Frontend."""

import streamlit as st
from ..config import THEME_CONFIG

def apply_global_styles():
    """Apply global CSS styles to the Streamlit app."""
    st.markdown(f"""
    <style>
        .main-header {{
            background: linear-gradient(90deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
            color: white;
        }}
        
        .chat-message {{
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .user-message {{
            background: linear-gradient(135deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            color: white;
            margin-left: 20%;
        }}
        
        .assistant-message {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            margin-right: 20%;
        }}
        
        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid {THEME_CONFIG['primary_color']};
        }}
        
        .profile-card {{
            background: linear-gradient(135deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 15px rgba(102, 126, 234, 0.3);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .profile-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .tax-card {{
            background: linear-gradient(135deg, {THEME_CONFIG['accent_color']} 0%, {THEME_CONFIG['success_color']} 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 15px rgba(79, 172, 254, 0.3);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .tax-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(79, 172, 254, 0.4);
        }}
        
        .expense-card {{
            background: linear-gradient(135deg, {THEME_CONFIG['warning_color']} 0%, #fee140 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 15px rgba(250, 112, 154, 0.3);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .expense-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(250, 112, 154, 0.4);
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .metric-label {{
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            display: block;
        }}
        
        .section-header {{
            background: linear-gradient(90deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            margin: 2rem 0 1rem 0;
            font-size: 1.2rem;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .sidebar-content {{
            background: linear-gradient(180deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
        }}
        
        .stButton > button {{
            background: linear-gradient(90deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            color: white;
            border: none;
            border-radius: 20px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            background: linear-gradient(90deg, #5a6fd8 0%, #6a4190 100%);
        }}
        
        .stButton > button:active {{
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .stButton > button:disabled {{
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }}
        
        .success-message {{
            background: linear-gradient(135deg, {THEME_CONFIG['accent_color']} 0%, {THEME_CONFIG['success_color']} 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
        }}
        
        .error-message {{
            background: linear-gradient(135deg, {THEME_CONFIG['error_color']} 0%, #ee5a24 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
        }}
        
        .markdown-content {{
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid {THEME_CONFIG['primary_color']};
        }}
        
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {{
            color: {THEME_CONFIG['primary_color']};
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }}
        
        .markdown-content ul, .markdown-content ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}
        
        .markdown-content li {{
            margin: 0.5rem 0;
        }}
        
        .markdown-content strong {{
            color: {THEME_CONFIG['secondary_color']};
        }}
        
        .markdown-content code {{
            background: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }}
        
        /* Chat Interface Improvements */
        .chat-container {{
            max-height: 70vh;
            overflow-y: auto;
            padding: 1rem;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            background: #fafafa;
        }}
        
        .chat-message {{
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .user-message {{
            background: linear-gradient(135deg, {THEME_CONFIG['primary_color']} 0%, {THEME_CONFIG['secondary_color']} 100%);
            color: white;
            margin-left: 20%;
            text-align: right;
        }}
        
        .assistant-message {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            margin-right: 20%;
        }}
        
        .processing-indicator {{
            background: linear-gradient(135deg, {THEME_CONFIG['accent_color']} 0%, {THEME_CONFIG['success_color']} 100%);
            color: white;
            padding: 1rem;
            border-radius: 15px;
            margin: 1rem 0;
            text-align: center;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
            100% {{ opacity: 1; }}
        }}
        
        .chat-input-container {{
            position: sticky;
            bottom: 0;
            background: white;
            padding: 1rem;
            border-top: 1px solid #e0e0e0;
            border-radius: 0 0 10px 10px;
        }}
        
        .welcome-message {{
            text-align: center;
            padding: 3rem 2rem;
            color: #666;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            margin: 2rem 0;
        }}
        
        /* Message states */
        .message-sent {{
            opacity: 1;
            border: 2px solid rgba(255,255,255,0.2);
        }}
        
        .message-typing {{
            opacity: 0.8;
            border: 2px dashed rgba(255,255,255,0.3);
            animation: typing 1.5s ease-in-out infinite;
        }}
        
        .message-processing {{
            opacity: 0.7;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        
        @keyframes typing {{
            0%, 100% {{ opacity: 0.8; }}
            50% {{ opacity: 0.6; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def get_navigation_styles():
    """Get styles for navigation menu."""
    return {
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": THEME_CONFIG["primary_color"], "font-size": "25px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "margin": "0px",
            "padding": "10px 20px",
            "color": "#333333",
            "background-color": "#ffffff",
            "border-radius": "8px",
            "--hover-color": "#e6e9ff"
        },
        "nav-link-selected": {
            "background-color": THEME_CONFIG["primary_color"],
            "color": "#ffffff",
            "border-radius": "8px"
        },
    }
