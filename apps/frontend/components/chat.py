"""Chat component for TaxFix Frontend."""

import streamlit as st
from datetime import datetime
from typing import Dict, List
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from services.api_client import APIClient
from auth.auth_manager import AuthManager
from utils.helpers import SessionHelper, StreamingHelper


def render_chat_interface(api_client: APIClient, auth_manager: AuthManager):
    """Render the main chat interface."""
    st.markdown("## 💬 Chat with TaxFix AI")
    
    # Initialize session ID if needed
    if not st.session_state.current_session_id:
        user = auth_manager.get_current_user()
        if user:
            user_id = user.get("id") or user.get("user_id", "unknown")
            st.session_state.current_session_id = SessionHelper.generate_session_id(user_id)
    
    # Display conversation history
    render_conversation_display()
    
    # Chat input form
    render_chat_input(api_client, auth_manager)


def render_conversation_display():
    """Render the conversation history."""
    if not st.session_state.conversation_history:
        st.markdown("""
        <div class="welcome-message">
            <h3>👋 Welcome to TaxFix!</h3>
            <p>Get answers about German tax questions and maintain & track your expenses for tax savings.</p>
            <p><strong>Start by asking a question below!</strong></p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Display messages using Streamlit's built-in chat interface
    for i, message in enumerate(st.session_state.conversation_history):
        role = message.get("role", "user")
        content = message.get("content", "")
        
        # Use Streamlit's native chat message display
        with st.chat_message(role):
            st.markdown(content)


def render_user_message(content: str, timestamp):
    """Render a user message."""
    st.markdown(f"""
    <div class="chat-message user-message">
        <div style="font-size: 0.8em; opacity: 0.8; margin-bottom: 0.5rem;">
            You • {format_timestamp(timestamp)}
        </div>
        <div>{content}</div>
    </div>
    """, unsafe_allow_html=True)


def render_assistant_message(content: str, timestamp):
    """Render an assistant message."""
    st.markdown(f"""
    <div class="chat-message assistant-message">
        <div style="font-size: 0.8em; opacity: 0.8; margin-bottom: 0.5rem;">
            TaxFix AI • {format_timestamp(timestamp)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Use markdown container for proper formatting
    with st.container():
        st.markdown(f'<div class="markdown-content">{content}</div>', unsafe_allow_html=True)


def render_chat_input(api_client: APIClient, auth_manager: AuthManager):
    """Render the chat input form."""
    st.markdown("---")
    
    # Initialize processing state
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    
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
    
    # Handle message sending
    if send_button and user_input and user_input.strip():
        handle_message_send(api_client, auth_manager, user_input.strip())


def handle_message_send(api_client: APIClient, auth_manager: AuthManager, message: str):
    """Handle sending a message and getting response."""
    st.session_state.is_processing = True
    
    try:
        # Add user message to history
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now()
        }
        st.session_state.conversation_history.append(user_message)
        
        # Show processing indicator
        with st.empty():
            st.markdown("""
            <div class="processing-indicator">
                <div>🤔 TaxFix AI is thinking...</div>
                <div style="font-size: 0.9em; margin-top: 0.5rem;">Analyzing your tax question...</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Send message to API
        token = auth_manager.get_token()
        session_id = st.session_state.current_session_id
        if not session_id:
            user_id = st.session_state.user.get("id") or st.session_state.user.get("user_id")
            session_id = SessionHelper.generate_session_id(user_id)
            st.session_state.current_session_id = session_id
        
        # Use streaming response with proper Streamlit chat interface
        try:
            # Stream into assistant bubble for live view
            assistant_box = st.chat_message("assistant")
            full_response = assistant_box.write_stream(
                StreamingHelper.block_stream(
                    api_client.send_message_streaming(message, session_id, token)
                )
            )
            response_content = full_response if isinstance(full_response, str) else ""
        except Exception as stream_error:
            # Fallback to non-streaming
            response = api_client.send_message(message, session_id, token)
            if response.get("success"):
                response_content = response.get("content", "I encountered an error processing your request.")
                # Render as Markdown once
                st.chat_message("assistant").markdown(response_content)
            else:
                response_content = f"Error: {response.get('error', 'Unknown error occurred')}"
                st.chat_message("assistant").markdown(response_content)
        
        # Add assistant response to history
        assistant_message = {
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now()
        }
        st.session_state.conversation_history.append(assistant_message)
        
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        # Add error response to history
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


def format_timestamp(timestamp) -> str:
    """Format timestamp for display."""
    if isinstance(timestamp, str):
        return timestamp
    try:
        return timestamp.strftime("%H:%M")
    except:
        return "Now"
