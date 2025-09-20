"""
Beautiful Streamlit Frontend for TaxFix Multi-Agent System.
"""
import streamlit as st
import requests
import json
import time
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(
    page_title="TaxFix - AI Tax Advisor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        margin-right: 20%;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .profile-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 15px rgba(102, 126, 234, 0.3);
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .profile-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(102, 126, 234, 0.4);
    }
    
    .tax-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 15px rgba(79, 172, 254, 0.3);
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .tax-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(79, 172, 254, 0.4);
    }
    
    .expense-card {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 15px rgba(250, 112, 154, 0.3);
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .expense-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(250, 112, 154, 0.4);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .section-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        margin: 2rem 0 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        background: linear-gradient(90deg, #5a6fd8 0%, #6a4190 100%);
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .stButton > button:disabled {
        background: #ccc;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }
    
    .success-message {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .markdown-content {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .markdown-content h1, .markdown-content h2, .markdown-content h3 {
        color: #667eea;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .markdown-content ul, .markdown-content ol {
        margin: 1rem 0;
        padding-left: 2rem;
    }
    
    .markdown-content li {
        margin: 0.5rem 0;
    }
    
    .markdown-content strong {
        color: #764ba2;
    }
    
    .markdown-content code {
        background: #f8f9fa;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
    }
    
    /* Chat Interface Improvements */
    .chat-container {
        max-height: 70vh;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background: #fafafa;
    }
    
    .chat-message {
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
        text-align: right;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        margin-right: 20%;
    }
    
    .processing-indicator {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .chat-input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1rem;
        border-top: 1px solid #e0e0e0;
        border-radius: 0 0 10px 10px;
    }
    
    .welcome-message {
        text-align: center;
        padding: 3rem 2rem;
        color: #666;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 15px;
        margin: 2rem 0;
    }
    
    /* Message states */
    .message-sent {
        opacity: 1;
        border: 2px solid rgba(255,255,255,0.2);
    }
    
    .message-typing {
        opacity: 0.8;
        border: 2px dashed rgba(255,255,255,0.3);
        animation: typing 1.5s ease-in-out infinite;
    }
    
    .message-processing {
        opacity: 0.7;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes typing {
        0%, 100% { opacity: 0.8; }
        50% { opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000"

class TaxFixFrontend:
    """Main frontend application class."""
    
    def __init__(self):
        self.api_base_url = API_BASE_URL
    
    def _clean_markdown_for_streaming(self, text: str) -> str:
        """Clean markdown text for streaming to avoid parsing errors while preserving valid formatting."""
        # Don't modify the text if it's already well-formatted
        # Only clean up obvious issues that would break markdown parsing
        
        # Check for incomplete markdown syntax that would cause errors
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Only fix lines that have clearly incomplete markdown
            if line.strip().endswith('**') and not line.strip().startswith('**') and line.count('**') == 1:
                # Incomplete bold formatting - remove the incomplete **
                cleaned_lines.append(line.replace('**', ''))
            elif line.strip().endswith('*') and not line.strip().startswith('*') and line.count('*') == 1:
                # Incomplete italic formatting - remove the incomplete *
                cleaned_lines.append(line.replace('*', ''))
            elif line.strip().endswith('`') and not line.strip().startswith('`') and line.count('`') == 1:
                # Incomplete code formatting - remove the incomplete `
                cleaned_lines.append(line.replace('`', ''))
            else:
                # Keep the line as-is (preserve valid markdown)
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _is_complete_markdown_block(self, text: str) -> bool:
        """Check if the text contains complete markdown blocks."""
        # Simple heuristic: if we have balanced markdown syntax, it's likely complete
        code_blocks = text.count('```')
        if code_blocks % 2 == 0 and code_blocks > 0:
            return True
        
        # Check for complete lists, headers, etc.
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith('#') or line.strip().startswith('*') or line.strip().startswith('-'):
                return True
        
        return False
    
    def _finalize_markdown(self, text: str) -> str:
        """Light post-formatting to improve Markdown after streaming completes."""
        try:
            # Normalize bullets at line start: •, *, – to '- '
            text = re.sub(r'(?m)^[ \t]*[•\*–][ \t]*', '- ', text)
            # Ensure blank line before list items and numbered items
            text = re.sub(r'(?<!\n)\n(-\s)', r"\n\1", text)
            text = re.sub(r'(?<!\n)(\d+)\.\s', r"\n\n\1. ", text)
            # Remove stray pipe-only lines
            text = re.sub(r'(?m)^\s*\|+\s*$', '', text)
            # Remove duplicated empty table cells like ' | | '
            text = re.sub(r'\s*\|\s*\|\s*', ' ', text)
            # Collapse excessive newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text
        except Exception:
            return text

    def _block_markdown_stream(self, token_iter):
        """
        Re-chunk incoming deltas so we only yield at safe Markdown block boundaries.
        Avoid yielding mid-list/table/heading, and never break code fences.
        """
        buf = ""
        code_fence_open = False
        fence_re = re.compile(r"```")

        def should_flush(b: str) -> bool:
            if not b:
                return False
            if code_fence_open:
                return False  # don't flush mid-code block
            if b.endswith("\n\n"):
                return True  # paragraph boundary
            # Evaluate the last non-empty line
            parts = b.split("\n")
            last_line = parts[-1]
            prev = parts[-2] if last_line == "" and len(parts) >= 2 else last_line
            return bool(re.match(r"^(\s*[-*] |\s*\d+\.\s|#+\s|\|.*\|)$", prev))

        for token in token_iter:
            if not token:
                continue
            buf += token

            if "```" in token:
                # Toggle code fence state on odd count per chunk
                if len(fence_re.findall(token)) % 2 == 1:
                    code_fence_open = not code_fence_open

            if should_flush(buf):
                yield buf
                buf = ""

        if buf:
            yield buf
    
    def _delta_markdown_stream(self, chunks_iter):
        """Yield only the new delta as-is to avoid altering Markdown mid-stream."""
        buffer = ""
        last_sent = 0
        for chunk in chunks_iter:
            if not chunk:
                continue
            buffer += chunk
            piece = buffer[last_sent:]
            if not piece:
                continue
            yield piece
            last_sent = len(buffer)
        
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
            self._check_url_auth_restore()
    
    def _check_url_auth_restore(self):
        """Check URL parameters for auth restoration after refresh."""
        try:
            # Simple approach: check URL for auth restoration
            query_params = st.query_params
            if query_params.get('auth_token') and query_params.get('user_id'):
                token = query_params['auth_token']
                user_id = query_params['user_id']
                
                # Validate token with backend using existing /auth/me endpoint
                validation_response = self.make_api_request(f"/auth/me?token={token}", "GET")
                if validation_response.get("success"):
                    user_data = validation_response.get("user")
                    # Check both possible user ID field names
                    actual_user_id = user_data.get("id") or user_data.get("user_id") if user_data else None
                    
                    if user_data and actual_user_id == user_id:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.session_state.token = token
                        
                        # Store in browser storage for future refreshes
                        self._store_session_in_storage()
                        
                        # Clean URL
                        st.query_params.clear()
                        st.rerun()
        except Exception as e:
            # If restoration fails, continue normally
            pass
    
    def _store_session_in_storage(self):
        """Store authentication session in browser storage."""
        if st.session_state.authenticated and st.session_state.user and st.session_state.token:
            # Escape user data for JavaScript
            user_json = json.dumps(st.session_state.user).replace("'", "\\'")
            token = st.session_state.token
            
            storage_script = f"""
            <script>
            sessionStorage.setItem('taxfix_auth', 'true');
            sessionStorage.setItem('taxfix_user', '{user_json}');
            sessionStorage.setItem('taxfix_token', '{token}');
            </script>
            """
            components.html(storage_script, height=0)
    
    def _clear_session_storage(self):
        """Clear authentication session from browser storage."""
        clear_script = """
        <script>
        sessionStorage.removeItem('taxfix_auth');
        sessionStorage.removeItem('taxfix_user');
        sessionStorage.removeItem('taxfix_token');
        localStorage.removeItem('taxfix_auth');
        localStorage.removeItem('taxfix_user');
        localStorage.removeItem('taxfix_token');
        </script>
        """
        components.html(clear_script, height=0)
    
    def make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None, token: str = None) -> Dict:
        """Make API request to backend."""
        url = f"{self.api_base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API Error: {response.status_code}", "details": response.text}
                
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to backend. Please make sure the backend is running."}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def login_user(self, email: str, password: str) -> bool:
        """Login user."""
        response = self.make_api_request("/auth/login", "POST", {
            "email": email,
            "password": password
        })
        
        if "error" not in response and response.get("success"):
            st.session_state.authenticated = True
            st.session_state.user = response.get("user")
            st.session_state.token = response.get("token")
            
            # Store authentication in browser storage for persistence
            self._store_session_in_storage()
            
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
    
    def register_user(self, name: str, email: str, password: str) -> bool:
        """Register user."""
        response = self.make_api_request("/auth/register", "POST", {
            "name": name,
            "email": email,
            "password": password
        })
        
        if "error" not in response and response.get("success"):
            st.success("Registration successful! Please login.")
            return True
        else:
            st.error(response.get("error", "Registration failed"))
            return False
    
    def logout_user(self):
        """Logout user."""
        if st.session_state.token:
            self.make_api_request("/auth/logout", "POST", token=st.session_state.token)
        
        # Clear session storage
        self._clear_session_storage()
        
        # Clear URL parameters
        st.query_params.clear()
        
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.token = None
        st.session_state.conversation_history = []
        st.session_state.current_session_id = None
        st.session_state.user_profile = None
    
    def send_message(self, message: str) -> Dict:
        """Send message to chat."""
        if not st.session_state.current_session_id:
            st.session_state.current_session_id = f"session_{st.session_state.user['user_id']}_{int(time.time())}"
        
        response = self.make_api_request("/chat/message", "POST", {
            "message": message,
            "session_id": st.session_state.current_session_id
        }, token=st.session_state.token)
        
        return response
    
    def send_message_streaming(self, message: str):
        """Send message to chat with streaming response."""
        if not st.session_state.current_session_id:
            st.session_state.current_session_id = f"session_{st.session_state.user['user_id']}_{int(time.time())}"
        
        url = f"{self.api_base_url}/chat/message/stream"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        
        if st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        
        try:
            with requests.post(
                url,
                json={
                    "message": message,
                    "session_id": st.session_state.current_session_id,
                },
                headers=headers,
                stream=True,
                timeout=300,
            ) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if raw.startswith("data: "):
                        data = raw[6:]
                        if data == "[DONE]":
                            break
                        # Parse JSON delta frames; fallback to raw text if parsing fails
                        try:
                            delta = json.loads(data).get("delta", "")
                        except Exception:
                            delta = data
                        if delta:
                            yield delta
        except requests.exceptions.Timeout:
            yield "Error: Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            yield "Error: Cannot connect to backend. Please make sure the backend is running."
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def get_user_profile(self) -> Dict:
        """Get user profile."""
        response = self.make_api_request("/user/profile", token=st.session_state.token)
        return response
    
    def create_user_profile(self, profile_data: Dict) -> Dict:
        """Create user profile."""
        response = self.make_api_request("/user/profile", "POST", profile_data, token=st.session_state.token)
        return response
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history."""
        response = self.make_api_request("/user/conversations", token=st.session_state.token)
        if "error" not in response and response.get("success"):
            return response.get("conversations", [])
        return []
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages for a specific conversation."""
        response = self.make_api_request(f"/conversation/{conversation_id}/messages", token=st.session_state.token)
        if "error" not in response and response.get("success"):
            return response.get("messages", [])
        return []
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        response = self.make_api_request(f"/conversation/{conversation_id}", "DELETE", token=st.session_state.token)
        return "error" not in response and response.get("success", False)
    
    def render_header(self):
        """Render main header."""
        st.markdown("""
        <div class="main-header">
            <h1>💰 TaxFix - AI Tax Advisor</h1>
            <p>Your Personal German Tax Assistant powered by Multi-Agent AI</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_auth_page(self):
        """Render authentication page."""
        st.markdown("### 🔐 Authentication")
        
        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("#### Login to your account")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password")
                login_button = st.form_submit_button("Login", use_container_width=True)
                
                if login_button:
                    if email and password:
                        if self.login_user(email, password):
                            st.rerun()
                    else:
                        st.error("Please fill in all fields")
        
        with tab2:
            st.markdown("#### Create a new account")
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                register_button = st.form_submit_button("Register", use_container_width=True)
                
                if register_button:
                    if name and email and password and confirm_password:
                        if password == confirm_password:
                            if self.register_user(name, email, password):
                                st.rerun()
                        else:
                            st.error("Passwords do not match")
                    else:
                        st.error("Please fill in all fields")
    
    def render_sidebar(self):
        """Render sidebar with user info and navigation."""
        with st.sidebar:
            st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
            
            # User info
            if st.session_state.user:
                st.markdown(f"### 👤 {st.session_state.user.get('name', 'User')}")
                st.markdown(f"📧 {st.session_state.user.get('email', '')}")
                
                # Logout button
                if st.button("🚪 Logout", use_container_width=True):
                    self.logout_user()
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Debug mode removed for production
            
            # Navigation
            st.markdown("### 🧭 Navigation")
            
            # Get user profile
            if st.session_state.authenticated and not st.session_state.user_profile:
                profile_response = self.get_user_profile()
                if "error" not in profile_response and profile_response.get("success"):
                    st.session_state.user_profile = profile_response.get("profile")
            
            # Profile info
            if st.session_state.user_profile:
                st.markdown("#### 📊 Your Profile")
                profile = st.session_state.user_profile
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Income", f"€{profile.get('annual_income', 0):,.0f}" if profile.get('annual_income') else "Not set")
                with col2:
                    st.metric("Dependents", profile.get('dependents', 0))
                
                st.markdown(f"**Status:** {profile.get('filing_status', 'Not set')}")
                st.markdown(f"**Employment:** {profile.get('employment_status', 'Not set')}")
            
            # Conversation history
            st.markdown("#### 💬 Recent Conversations")
            conversations = self.get_conversation_history()
            
            if conversations:
                # Add "New Chat" option
                if st.button("➕ New Chat", use_container_width=True):
                    st.session_state.current_session_id = None
                    st.session_state.conversation_history = []
                    st.session_state.switch_to_chat = True
                    st.rerun()
                
                st.markdown("---")
                
                for conv in conversations[-10:]:  # Show last 10
                    # Create a unique key for each conversation button
                    conv_key = f"conv_{conv['id']}"
                    
                    # Format the conversation display
                    conv_title = conv.get('title', f"Chat {conv['created_at'][:10]}")
                    conv_date = conv['created_at'][:10]
                    conv_time = conv['created_at'][11:16]
                    message_count = conv.get('message_count', 0)
                    
                    # Create columns for conversation and delete button
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # Create button for conversation
                        if st.button(
                            f"💬 {conv_title}\n📅 {conv_date} {conv_time}\n📝 {message_count} messages",
                            key=conv_key,
                            use_container_width=True
                        ):
                            # Load this conversation
                            st.session_state.current_session_id = conv['id']
                            messages = self.get_conversation_messages(conv['id'])
                            
                            # Convert messages to conversation history format
                            st.session_state.conversation_history = []
                            for msg in messages:
                                st.session_state.conversation_history.append({
                                    "role": msg['role'],
                                    "content": msg['content'],
                                    "timestamp": datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')) if msg['timestamp'] else datetime.now()
                                })
                            st.rerun()
                    
                    with col2:
                        # Delete button
                        if st.button("🗑️", key=f"delete_{conv['id']}", help="Delete conversation"):
                            if self.delete_conversation(conv['id']):
                                st.success("Conversation deleted!")
                                # Clear current conversation if it was deleted
                                if st.session_state.current_session_id == conv['id']:
                                    st.session_state.current_session_id = None
                                    st.session_state.conversation_history = []
                                st.rerun()
                            else:
                                st.error("Failed to delete conversation")
            else:
                st.markdown("No conversations yet")
                if st.button("➕ Start New Chat", use_container_width=True):
                    st.session_state.current_session_id = None
                    st.session_state.conversation_history = []
                    st.session_state.switch_to_chat = True
                    st.rerun()
    
    def render_chat_interface(self):
        """Render modern, dynamic chat interface."""
        st.markdown("### 💬 Chat with TaxFix AI")
        
        # Initialize chat state
        if 'chat_input' not in st.session_state:
            st.session_state.chat_input = ""
        if 'is_processing' not in st.session_state:
            st.session_state.is_processing = False
        
        # Render past messages using Streamlit chat API
        if st.session_state.conversation_history:
            for m in st.session_state.conversation_history:
                bubble = st.chat_message("user" if m["role"] == "user" else "assistant")
                bubble.markdown(m["content"])
        else:
            st.markdown("""
            <div class="welcome-message">
                <h4>👋 Welcome to TaxFix AI!</h4>
                <p>Ask me anything about German taxes, deductions, or tax planning.</p>
                <p style=\"font-size: 0.9em; margin-top: 1rem;\">
                    💡 <strong>Try asking:</strong> "What deductions can I claim?" or "How do I calculate my tax liability?"
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Modern chat input with better UX
        st.markdown("---")
        
        # Chat input with proper Enter key handling
        with st.form("chat_form", clear_on_submit=False):
            col1, col2 = st.columns([4, 1])
            with col1:
                # Check for pre-filled message from dashboard
                prefill_value = st.session_state.get('prefill_message', '')
                # Don't clear prefill_message here - clear it only after successful send
                
                user_input = st.text_input(
                    "Ask me anything about German taxes...", 
                    value=prefill_value,
                    placeholder="What are the tax deductions I can claim?",
                    key=f"chat_input_field_{st.session_state.get('input_clear_counter', 0)}",
                    disabled=st.session_state.is_processing,
                    help="Press Enter or click Send to submit your message"
                )
            with col2:
                send_button = st.form_submit_button(
                    "Send" if not st.session_state.is_processing else "Processing...",
                    use_container_width=True,
                    disabled=st.session_state.is_processing
                )
        
        # Chat interface ready for production use
        
        # Handle message sending - form submission
        if send_button and user_input and user_input.strip():
            # Set processing state
            st.session_state.is_processing = True
            
            # Generate new session ID if starting new conversation
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = f"session_{st.session_state.user['user_id']}_{int(time.time())}"
            
            # Store the message content for processing
            message_to_send = user_input.strip()
            
            # Immediately show the user message bubble
            st.chat_message("user").markdown(message_to_send)
            # Persist to history
            st.session_state.conversation_history.append({
                "role": "user",
                "content": message_to_send,
                "timestamp": datetime.now(),
                "sent": True
            })
            
            # Show processing indicator with better styling
            processing_placeholder = st.empty()
            processing_placeholder.markdown("""
            <div class="processing-indicator">
                🤔 TaxFix AI is thinking...
            </div>
            """, unsafe_allow_html=True)
            
            try:
                # Send message to backend with streaming
                processing_placeholder.empty()
                
                # Create a placeholder for streaming response
                response_placeholder = st.empty()
                full_response = ""
                
                # Simple: render final assistant response as Markdown (non-streaming fallback)
                try:
                    processing_placeholder.empty()
                    # Stream into assistant bubble for live view, flushing at Markdown block boundaries
                    assistant_box = st.chat_message("assistant")
                    full_response = assistant_box.write_stream(
                        self._block_markdown_stream(self.send_message_streaming(message_to_send))
                    )
                except Exception as stream_error:
                    # Fallback to non-streaming if streaming fails
                    st.warning("Streaming failed, using regular response...")
                    response = self.send_message(message_to_send)
                    if "error" not in response and response.get("content"):
                        full_response = response["content"]
                        # Render as Markdown once
                        st.chat_message("assistant").markdown(self._finalize_markdown(full_response))
                    else:
                        full_response = "I apologize, but I encountered an error processing your request. Please try again."
                
                # Add final assistant response to history (no post-mangle; keep exactly what was rendered)
                assistant_message = {
                    "role": "assistant",
                    "content": full_response if isinstance(full_response, str) else "",
                    "timestamp": datetime.now()
                }
                st.session_state.conversation_history.append(assistant_message)
                
                # Clear the response placeholder
                response_placeholder.empty()
                
            except Exception as e:
                processing_placeholder.empty()
                
                error_response = {
                    "role": "assistant",
                    "content": f"Error: {str(e)}",
                    "timestamp": datetime.now()
                }
                st.session_state.conversation_history.append(error_response)
            
            finally:
                # Reset processing state
                st.session_state.is_processing = False
                
                # Clear the prefill message after successful send
                if 'prefill_message' in st.session_state:
                    del st.session_state.prefill_message
                
                # Clear the input field after response is complete
                st.session_state.input_clear_counter = st.session_state.get('input_clear_counter', 0) + 1
                
                # Rerun to update the display
                st.rerun()
        
        # Add some JavaScript for better UX
        st.markdown("""
        <script>
        // Auto-scroll to bottom of chat
        window.scrollTo(0, document.body.scrollHeight);
        
        // Focus on input field and handle Enter key
        document.addEventListener('DOMContentLoaded', function() {
            const input = document.querySelector('input[data-testid="textInput"]');
            if (input) {
                input.focus();
                
                // Handle Enter key press
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        // Find and click the submit button
                        const submitButton = document.querySelector('button[data-testid="baseButton-secondary"]');
                        if (submitButton && !submitButton.disabled) {
                            submitButton.click();
                        }
                    }
                });
            }
        });
        </script>
        """, unsafe_allow_html=True)
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data from API."""
        response = self.make_api_request("/user/dashboard-data", token=st.session_state.token)
        if "error" not in response and response.get("success"):
            return response
        else:
            st.error(f"Failed to load dashboard data: {response.get('error', 'Unknown error')}")
            return {}

    def render_dashboard(self):
        """Render comprehensive tax dashboard with all user data."""
        st.markdown("### 📊 Comprehensive Tax Dashboard")
        
        # Load dashboard data
        dashboard_data = self.get_dashboard_data()
        if not dashboard_data:
            return
            
        profile = dashboard_data.get("profile")
        expenses_data = dashboard_data.get("expenses", {})
        tax_calculations = dashboard_data.get("tax_calculations", {})
        tax_documents = dashboard_data.get("tax_documents", [])
        
        if not profile:
            st.warning("Please complete your profile to see personalized insights.")
            return
        
        # === PROFILE OVERVIEW SECTION ===
        st.markdown('<div class="section-header">👤 Profile Overview</div>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            employment_status = profile.get('employment_status', 'Not set').replace('_', ' ').title()
            st.markdown(f'''
            <div class="profile-card">
                <div class="metric-icon">💼</div>
                <div class="metric-label">Employment</div>
                <div class="metric-value">{employment_status}</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            filing_status = profile.get('filing_status', 'Not set').replace('_', ' ').title()
            st.markdown(f'''
            <div class="profile-card">
                <div class="metric-icon">📋</div>
                <div class="metric-label">Filing Status</div>
                <div class="metric-value">{filing_status}</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            dependents = profile.get('dependents', 0)
            dependents_icon = "👨‍👩‍👧‍👦" if dependents > 0 else "👤"
            st.markdown(f'''
            <div class="profile-card">
                <div class="metric-icon">{dependents_icon}</div>
                <div class="metric-label">Dependents</div>
                <div class="metric-value">{dependents}</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col4:
            risk_tolerance = profile.get('risk_tolerance', 'Not set').title()
            risk_icon = {"Conservative": "🛡️", "Moderate": "⚖️", "Aggressive": "🚀"}.get(risk_tolerance, "❓")
            st.markdown(f'''
            <div class="profile-card">
                <div class="metric-icon">{risk_icon}</div>
                <div class="metric-label">Risk Level</div>
                <div class="metric-value">{risk_tolerance}</div>
            </div>
            ''', unsafe_allow_html=True)

        # === TAX SUMMARY SECTION ===
        if tax_calculations:
            st.markdown('<div class="section-header">💰 Tax Summary</div>', unsafe_allow_html=True)
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                gross_income = tax_calculations.get('annual_income', 0)
                st.markdown(f'''
                <div class="tax-card">
                    <div class="metric-icon">💵</div>
                    <div class="metric-label">Gross Income</div>
                    <div class="metric-value">€{gross_income:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                taxable_income = tax_calculations.get('taxable_income', 0)
                st.markdown(f'''
                <div class="tax-card">
                    <div class="metric-icon">📊</div>
                    <div class="metric-label">Taxable Income</div>
                    <div class="metric-value">€{taxable_income:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col3:
                income_tax = tax_calculations.get('income_tax', 0)
                st.markdown(f'''
                <div class="tax-card">
                    <div class="metric-icon">🏛️</div>
                    <div class="metric-label">Income Tax</div>
                    <div class="metric-value">€{income_tax:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col4:
                total_tax = tax_calculations.get('total_tax', 0)
                st.markdown(f'''
                <div class="tax-card">
                    <div class="metric-icon">💸</div>
                    <div class="metric-label">Total Tax</div>
                    <div class="metric-value">€{total_tax:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col5:
                net_income = tax_calculations.get('net_income', 0)
                st.markdown(f'''
                <div class="tax-card">
                    <div class="metric-icon">💎</div>
                    <div class="metric-label">Net Income</div>
                    <div class="metric-value">€{net_income:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)

        # === EXPENSES SECTION ===
        st.markdown('<div class="section-header">💳 Expense Tracking</div>', unsafe_allow_html=True)
        
        expenses_summary = expenses_data.get("summary", {})
        expenses_list = expenses_data.get("items", [])
        
        if expenses_summary and expenses_summary.get("total_expenses", 0) > 0:
            # Expense summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_expenses = expenses_summary.get("total_expenses", 0)
                st.markdown(f'''
                <div class="expense-card">
                    <div class="metric-icon">📋</div>
                    <div class="metric-label">Total Expenses</div>
                    <div class="metric-value">{total_expenses}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                total_amount = expenses_summary.get('total_amount', 0)
                st.markdown(f'''
                <div class="expense-card">
                    <div class="metric-icon">💰</div>
                    <div class="metric-label">Total Amount</div>
                    <div class="metric-value">€{total_amount:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col3:
                average_expense = expenses_summary.get('average_expense', 0)
                st.markdown(f'''
                <div class="expense-card">
                    <div class="metric-icon">📊</div>
                    <div class="metric-label">Average Expense</div>
                    <div class="metric-value">€{average_expense:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col4:
                # Calculate potential tax savings (simplified)
                potential_savings = expenses_summary.get('total_amount', 0) * 0.3  # Rough estimate
                st.markdown(f'''
                <div class="expense-card">
                    <div class="metric-icon">💎</div>
                    <div class="metric-label">Est. Tax Savings</div>
                    <div class="metric-value">€{potential_savings:,.0f}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            # Expense category breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 📊 Expenses by Category")
                category_breakdown = expenses_summary.get("category_breakdown", {})
                if category_breakdown:
                    # Create pie chart for categories
                    categories = list(category_breakdown.keys())
                    amounts = list(category_breakdown.values())
                    
                    fig = px.pie(
                        values=amounts,
                        names=categories,
                        title="Expense Categories",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No expense categories to display")
            
            with col2:
                st.markdown("##### 📅 Monthly Spending")
                monthly_breakdown = expenses_summary.get("monthly_breakdown", {})
                if monthly_breakdown:
                    # Create bar chart for monthly spending
                    months = list(monthly_breakdown.keys())
                    amounts = list(monthly_breakdown.values())
                    
                    fig = px.bar(
                        x=months,
                        y=amounts,
                        title="Monthly Spending",
                        labels={"x": "Month", "y": "Amount (€)"},
                        color=amounts,
                        color_continuous_scale="viridis"
                    )
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No monthly data to display")
            
            # Recent expenses table
            st.markdown("##### 📝 Recent Expenses")
            if expenses_list:
                recent_expenses = sorted(expenses_list, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
                expense_df = pd.DataFrame([
                    {
                        "Description": exp.get("description", ""),
                        "Amount": f"€{exp.get('amount', 0):.2f}",
                        "Category": exp.get("category", "").title(),
                        "Date": exp.get("date_incurred", ""),
                        "Status": exp.get("status", "").title()
                    }
                    for exp in recent_expenses
                ])
                st.dataframe(expense_df, use_container_width=True)
            else:
                st.info("No expenses recorded yet")
        else:
            st.markdown('''
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 2rem;
                border-radius: 15px;
                text-align: center;
                margin: 1rem 0;
                box-shadow: 0 8px 15px rgba(240, 147, 251, 0.3);
            ">
                <div style="font-size: 3rem; margin-bottom: 1rem;">💡</div>
                <h3>Start Your Tax Optimization Journey!</h3>
                <p style="font-size: 1.1rem; margin: 1rem 0;">Track your expenses to unlock detailed analytics and maximize your tax deductions</p>
            </div>
            ''', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("💬 Ask AI to Help Track Expenses", use_container_width=True):
                    # Switch to chat tab with pre-filled message
                    st.session_state.switch_to_chat = True
                    st.session_state.prefill_message = "Help me track my tax-deductible expenses"
                    st.rerun()

        # === TAX BREAKDOWN VISUALIZATION ===
        if tax_calculations:
            st.markdown('<div class="section-header">📈 Tax Breakdown Analysis</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🥧 Tax Composition")
                # Tax breakdown pie chart
                tax_components = {
                    'Income Tax': tax_calculations.get('income_tax', 0),
                    'Solidarity Surcharge': tax_calculations.get('solidarity_surcharge', 0),
                    'Church Tax': tax_calculations.get('church_tax', 0),
                    'Net Income': tax_calculations.get('net_income', 0)
                }
                
                fig = px.pie(
                    values=list(tax_components.values()),
                    names=list(tax_components.keys()),
                    title="Income Distribution",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("##### 📊 Tax Rate Analysis")
                effective_rate = tax_calculations.get('effective_tax_rate', 0)
                
                # Tax rate gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=effective_rate,
                    title={'text': "Effective Tax Rate (%)"},
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={
                        'axis': {'range': [0, 50]},
                        'bar': {'color': "#667eea"},
                        'steps': [
                            {'range': [0, 15], 'color': "lightgray"},
                            {'range': [15, 30], 'color': "gray"},
                            {'range': [30, 50], 'color': "darkgray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 42
                        }
                    }
                ))
                st.plotly_chart(fig, use_container_width=True)

        # === OPTIMIZATION SUGGESTIONS ===
        st.markdown('<div class="section-header">💡 Smart Tax Optimization</div>', unsafe_allow_html=True)
        
        suggestions = []
        
        # Income-based suggestions
        income = tax_calculations.get('annual_income', 0) if tax_calculations else profile.get('annual_income', 0)
        if income > 50000:
            suggestions.append({
                "icon": "🏦",
                "title": "Riester Pension Contribution",
                "description": "Consider contributing to a Riester pension for tax benefits",
                "potential_savings": "Up to €2,100/year"
            })
        
        # Family-based suggestions
        if profile.get('dependents', 0) > 0:
            suggestions.append({
                "icon": "👶",
                "title": "Child Allowance (Kinderfreibetrag)",
                "description": "Ensure you're claiming all child-related tax benefits",
                "potential_savings": f"€{profile.get('dependents', 0) * 3648}/year"
            })
        
        # Employment-based suggestions
        if profile.get('employment_status') == 'employed':
            suggestions.append({
                "icon": "💼",
                "title": "Work-Related Expenses (Werbungskosten)",
                "description": "Track commuting, equipment, and professional development costs",
                "potential_savings": "Up to €1,000/year"
            })
        
        # Expense-based suggestions
        if expenses_summary and expenses_summary.get("total_amount", 0) > 1000:
            suggestions.append({
                "icon": "📊",
                "title": "Expense Optimization",
                "description": "Review and categorize expenses for maximum deductions",
                "potential_savings": f"€{expenses_summary.get('total_amount', 0) * 0.25:.0f}/year"
            })
        
        # Health & Insurance
        suggestions.append({
            "icon": "🏥",
            "title": "Health & Insurance Deductions",
            "description": "Maximize health insurance and pension contribution deductions",
            "potential_savings": "Up to €1,900/year"
        })
        
        # Display suggestions in cards
        if suggestions:
            for i, suggestion in enumerate(suggestions):
                with st.expander(f"{suggestion['icon']} {suggestion['title']} - {suggestion['potential_savings']}"):
                    st.markdown(f"**{suggestion['description']}**")
                    st.markdown(f"💰 **Potential Annual Savings:** {suggestion['potential_savings']}")
                    if st.button(f"💬 Learn More About {suggestion['title']}", key=f"suggestion_{i}"):
                        st.session_state.switch_to_chat = True
                        st.session_state.prefill_message = f"Tell me more about {suggestion['title']} and how I can benefit from it"
                        st.rerun()
        
        # === ACTION BUTTONS ===
        st.markdown('<div class="section-header">🚀 Quick Actions</div>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💬 Ask Tax Question", use_container_width=True):
                st.session_state.switch_to_chat = True
                st.session_state.prefill_message = "I have a tax question about"
                st.rerun()
        
        with col2:
            if st.button("📝 Add Expense", use_container_width=True):
                st.session_state.switch_to_chat = True
                st.session_state.prefill_message = "Help me add a new expense"
                st.rerun()
        
        with col3:
            if st.button("🔍 Review Deductions", use_container_width=True):
                st.session_state.switch_to_chat = True
                st.session_state.prefill_message = "Help me review my tax deductions"
                st.rerun()
        
        with col4:
            if st.button("📊 Update Profile", use_container_width=True):
                st.session_state.switch_to_chat = True
                st.session_state.prefill_message = "Help me update my tax profile"
                st.rerun()
        
        # Note: Chat switching is now handled in the main navigation logic
    
    def render_profile_creation_page(self):
        """Render beautiful profile creation page."""
        st.markdown('<div class="section-header">👤 Create Your Tax Profile</div>', unsafe_allow_html=True)
        
        # Welcome message with user info
        user = st.session_state.user
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin: 1rem 0 2rem 0;
            box-shadow: 0 8px 15px rgba(79, 172, 254, 0.3);
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🎉</div>
            <h2 style="margin: 0;">Welcome, {user.get('name', 'User')}!</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Let's create your personalized tax profile to provide you with the best advice</p>
        </div>
        ''', unsafe_allow_html=True)
        
        with st.form("create_profile_form"):
            st.markdown("#### 📊 Basic Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                employment_status = st.selectbox(
                    "Employment Status",
                    ["employed", "self-employed", "unemployed", "retired"],
                    help="Select your current employment status"
                )
                
                annual_income = st.number_input(
                    "Annual Income (€)",
                    min_value=0,
                    step=1000,
                    help="Your gross annual income in Euros"
                )
                
                dependents = st.number_input(
                    "Number of Dependents",
                    min_value=0,
                    max_value=10,
                    help="Number of people you financially support"
                )
            
            with col2:
                filing_status = st.selectbox(
                    "Filing Status",
                    ["single", "married_joint", "married_separate", "head_of_household"],
                    help="Your tax filing status"
                )
                
                risk_tolerance = st.selectbox(
                    "Risk Tolerance",
                    ["conservative", "moderate", "aggressive"],
                    help="Your comfort level with tax strategies"
                )
                
                tax_complexity_level = st.selectbox(
                    "Tax Knowledge Level",
                    ["beginner", "intermediate", "advanced"],
                    help="Your level of tax knowledge"
                )
            
            st.markdown("#### 🎯 Tax Goals")
            tax_goals = st.multiselect(
                "What are your main tax goals?",
                ["maximize_deductions", "reduce_tax_liability", "plan_for_retirement", "optimize_investments", "minimize_audit_risk"],
                default=["maximize_deductions", "reduce_tax_liability"],
                help="Select all that apply"
            )
            
            st.markdown("#### 💬 Communication Preferences")
            communication_style = st.selectbox(
                "Preferred Communication Style",
                ["friendly", "professional", "detailed", "concise"],
                help="How would you like us to communicate with you?"
            )
            
            if st.form_submit_button("Create Profile", use_container_width=True):
                if annual_income <= 0:
                    st.error("Please enter a valid annual income.")
                else:
                    # Create profile data
                    profile_data = {
                        "employment_status": employment_status,
                        "filing_status": filing_status,
                        "annual_income": annual_income,
                        "dependents": dependents,
                        "preferred_deductions": [],
                        "tax_goals": tax_goals,
                        "risk_tolerance": risk_tolerance,
                        "preferred_communication_style": communication_style,
                        "tax_complexity_level": tax_complexity_level
                    }
                    
                    # Send to backend
                    response = self.create_user_profile(profile_data)
                    
                    if "error" not in response and response.get("success"):
                        st.success("Profile created successfully!")
                        st.session_state.user_profile = response.get("profile")
                        st.rerun()
                    else:
                        st.error(f"Error creating profile: {response.get('error', 'Unknown error')}")

    def render_profile_page(self):
        """Render beautiful profile management page."""
        st.markdown('<div class="section-header">👤 Profile Management</div>', unsafe_allow_html=True)
        
        if st.session_state.user_profile:
            profile = st.session_state.user_profile
            user = st.session_state.user
            
            # === USER INFO HEADER ===
            st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem;
                border-radius: 15px;
                text-align: center;
                margin: 1rem 0 2rem 0;
                box-shadow: 0 8px 15px rgba(102, 126, 234, 0.3);
            ">
                <div style="font-size: 4rem; margin-bottom: 1rem;">👤</div>
                <h2 style="margin: 0;">{user.get('name', 'User')} Profile</h2>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">{user.get('email', '')}</p>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.form("profile_form"):
                # === PERSONAL INFORMATION ===
                st.markdown('<div class="section-header">📋 Personal Information</div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Auto-populate from logged-in user data
                    name = st.text_input(
                        "👤 Full Name", 
                        value=user.get('name', ''),
                        help="Your full name as registered"
                    )
                
                with col2:
                    # Email from logged-in user (read-only)
                    email = st.text_input(
                        "📧 Email Address", 
                        value=user.get('email', ''), 
                        disabled=True,
                        help="Email cannot be changed here"
                    )
                
                with col3:
                    dependents = st.number_input(
                        "👨‍👩‍👧‍👦 Dependents", 
                        value=int(profile.get('dependents', 0)), 
                        min_value=0, 
                        max_value=10,
                        help="Number of people you financially support"
                    )
                
                # === FINANCIAL INFORMATION ===
                st.markdown('<div class="section-header">💰 Financial Information</div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    annual_income = st.number_input(
                        "💵 Annual Income (€)", 
                        value=float(profile.get('annual_income', 0)), 
                        min_value=0.0, 
                        step=1000.0,
                        help="Your gross annual income in Euros"
                    )
                
                with col2:
                    employment_status = st.selectbox(
                        "💼 Employment Status",
                        ["employed", "self-employed", "unemployed", "retired"],
                        index=["employed", "self-employed", "unemployed", "retired"].index(profile.get('employment_status', 'employed')),
                        help="Your current employment situation"
                    )
                
                with col3:
                    filing_status = st.selectbox(
                        "📋 Filing Status",
                        ["single", "married_joint", "married_separate", "head_of_household"],
                        index=["single", "married_joint", "married_separate", "head_of_household"].index(profile.get('filing_status', 'single')),
                        help="Your tax filing status"
                    )
                
                # === TAX PREFERENCES ===
                st.markdown('<div class="section-header">🎯 Tax Preferences</div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    risk_tolerance = st.selectbox(
                        "🛡️ Risk Tolerance",
                        ["conservative", "moderate", "aggressive"],
                        index=["conservative", "moderate", "aggressive"].index(profile.get('risk_tolerance', 'conservative')),
                        help="Your comfort level with tax strategies"
                    )
                
                with col2:
                    tax_complexity_level = st.selectbox(
                        "🧠 Tax Knowledge Level",
                        ["beginner", "intermediate", "advanced"],
                        index=["beginner", "intermediate", "advanced"].index(profile.get('tax_complexity_level', 'beginner')),
                        help="Your level of tax knowledge"
                    )
                
                with col3:
                    communication_style = st.selectbox(
                        "💬 Communication Style",
                        ["friendly", "professional", "detailed", "concise"],
                        index=["friendly", "professional", "detailed", "concise"].index(profile.get('preferred_communication_style', 'friendly')),
                        help="How would you like us to communicate with you?"
                    )
                
                # === TAX GOALS ===
                st.markdown('<div class="section-header">🎯 Tax Goals</div>', unsafe_allow_html=True)
                
                # Create visual goal selection
                goals_options = {
                    "maximize_deductions": {"icon": "💰", "label": "Maximize Deductions", "desc": "Find all possible tax deductions"},
                    "reduce_tax_liability": {"icon": "📉", "label": "Reduce Tax Liability", "desc": "Lower your overall tax burden"},
                    "plan_for_retirement": {"icon": "🏦", "label": "Plan for Retirement", "desc": "Tax-efficient retirement planning"},
                    "optimize_investments": {"icon": "📈", "label": "Optimize Investments", "desc": "Investment tax optimization"},
                    "minimize_audit_risk": {"icon": "🛡️", "label": "Minimize Audit Risk", "desc": "Keep tax filings audit-safe"}
                }
                
                st.markdown("Select your main tax goals:")
                tax_goals = st.multiselect(
                    "Tax Goals",
                    options=list(goals_options.keys()),
                    default=profile.get('tax_goals', ["maximize_deductions", "reduce_tax_liability"]),
                    format_func=lambda x: f"{goals_options[x]['icon']} {goals_options[x]['label']} - {goals_options[x]['desc']}",
                    help="Select all goals that apply to your situation"
                )
                
                # === PROFILE SUMMARY ===
                if st.session_state.get('show_profile_summary', False):
                    st.markdown('<div class="section-header">📊 Profile Summary</div>', unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown(f'''
                        <div class="profile-card">
                            <div class="metric-icon">💼</div>
                            <div class="metric-label">Employment</div>
                            <div class="metric-value">{employment_status.replace('_', ' ').title()}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f'''
                        <div class="tax-card">
                            <div class="metric-icon">💵</div>
                            <div class="metric-label">Annual Income</div>
                            <div class="metric-value">€{annual_income:,.0f}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    
                    with col3:
                        risk_icon = {"conservative": "🛡️", "moderate": "⚖️", "aggressive": "🚀"}.get(risk_tolerance, "❓")
                        st.markdown(f'''
                        <div class="expense-card">
                            <div class="metric-icon">{risk_icon}</div>
                            <div class="metric-label">Risk Level</div>
                            <div class="metric-value">{risk_tolerance.title()}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown(f'''
                        <div class="profile-card">
                            <div class="metric-icon">🎯</div>
                            <div class="metric-label">Tax Goals</div>
                            <div class="metric-value">{len(tax_goals)} Selected</div>
                        </div>
                        ''', unsafe_allow_html=True)
                
                # === ACTION BUTTONS ===
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    update_button = st.form_submit_button(
                        "💾 Update Profile", 
                        use_container_width=True,
                        help="Save your profile changes"
                    )
                
                if update_button:
                    # Create updated profile data
                    updated_profile_data = {
                        "employment_status": employment_status,
                        "filing_status": filing_status,
                        "annual_income": annual_income,
                        "dependents": dependents,
                        "preferred_deductions": profile.get('preferred_deductions', []),
                        "tax_goals": tax_goals,
                        "risk_tolerance": risk_tolerance,
                        "preferred_communication_style": communication_style,
                        "tax_complexity_level": tax_complexity_level
                    }
                    
                    # Update profile via API
                    response = self.create_user_profile(updated_profile_data)
                    
                    if "error" not in response and response.get("success"):
                        st.success("🎉 Profile updated successfully!")
                        st.session_state.user_profile = response.get("profile")
                        st.session_state.show_profile_summary = True
                        st.rerun()
                    else:
                        st.error(f"❌ Error updating profile: {response.get('error', 'Unknown error')}")
            
            # === QUICK ACTIONS ===
            st.markdown('<div class="section-header">🚀 Quick Actions</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 View Dashboard", use_container_width=True):
                    st.session_state.switch_to_dashboard = True
                    st.rerun()
            
            with col2:
                if st.button("💬 Get Tax Advice", use_container_width=True):
                    st.session_state.switch_to_chat = True
                    st.session_state.prefill_message = "Based on my profile, what tax advice do you have for me?"
                    st.rerun()
            
            with col3:
                if st.button("🔍 Profile Summary", use_container_width=True):
                    st.session_state.show_profile_summary = not st.session_state.get('show_profile_summary', False)
                    st.rerun()
                    
        else:
            st.warning("Profile not found. Please contact support.")
    
    def run(self):
        """Run the main application."""
        self.init_session_state()
        self.render_header()
        
        if not st.session_state.authenticated:
            self.render_auth_page()
        else:
            # Check if user has a profile
            if st.session_state.authenticated and not st.session_state.user_profile:
                profile_response = self.get_user_profile()
                if "error" not in profile_response and profile_response.get("success"):
                    st.session_state.user_profile = profile_response.get("profile")
                elif "error" not in profile_response and not profile_response.get("success"):
                    # No profile found, show profile creation page
                    self.render_profile_creation_page()
                    return
            
            # If still no profile after check, show creation page
            if not st.session_state.user_profile:
                self.render_profile_creation_page()
                return
            
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
                styles={
                    "container": {"padding": "0!important", "background-color": "#fafafa"},
                    "icon": {"color": "#667eea", "font-size": "25px"},
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
                        "background-color": "#667eea",
                        "color": "#ffffff",
                        "border-radius": "8px"
                    },
                }
            )
            
            # Store current tab
            st.session_state.current_tab = selected
            
            # Tab switching working correctly
            
            # Render sidebar
            self.render_sidebar()
            
            # Render selected page
            if selected == "Chat":
                self.render_chat_interface()
            elif selected == "Dashboard":
                self.render_dashboard()
            elif selected == "Profile":
                self.render_profile_page()


# Run the application
if __name__ == "__main__":
    app = TaxFixFrontend()
    app.run()
