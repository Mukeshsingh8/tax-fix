"""Sidebar component for TaxFix Frontend."""

import streamlit as st
from typing import Dict, List
from ..auth.auth_manager import AuthManager
from ..services.api_client import APIClient


def render_sidebar(auth_manager: AuthManager, api_client: APIClient):
    """Render the sidebar with user info and navigation."""
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        
        # User info section
        user = auth_manager.get_current_user()
        if user:
            st.markdown("### 👤 User Info")
            st.write(f"**Name:** {user.get('name', 'Unknown')}")
            st.write(f"**Email:** {user.get('email', 'Unknown')}")
            st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.current_session_id = None
            st.session_state.switch_to_chat = True
            st.rerun()
        
        if st.button("📊 View Dashboard", use_container_width=True):
            st.session_state.switch_to_dashboard = True
            st.rerun()
        
        if st.button("⚙️ Profile Settings", use_container_width=True):
            st.session_state.current_tab = "Profile"
            st.rerun()
        
        st.markdown("---")
        
        # Conversation history
        render_conversation_history(api_client, auth_manager.get_token())
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.logout()
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_conversation_history(api_client: APIClient, token: str):
    """Render conversation history in sidebar."""
    st.markdown("### 💬 Recent Chats")
    
    try:
        response = api_client.get_conversations(token)
        if response.get("success") and response.get("conversations"):
            conversations = response["conversations"]
            
            # Limit to recent 5 conversations
            recent_conversations = conversations[:5]
            
            for conv in recent_conversations:
                title = conv.get("title", "Untitled Chat")
                conversation_id = conv.get("id")
                
                # Truncate long titles
                if len(title) > 30:
                    title = title[:27] + "..."
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if st.button(title, key=f"conv_{conversation_id}", use_container_width=True):
                        load_conversation(api_client, conversation_id, token)
                
                with col2:
                    if st.button("🗑️", key=f"del_{conversation_id}"):
                        delete_conversation(api_client, conversation_id, token)
        else:
            st.write("No conversations yet")
            
    except Exception as e:
        st.write("Unable to load conversations")


def load_conversation(api_client: APIClient, conversation_id: str, token: str):
    """Load a specific conversation."""
    try:
        response = api_client.get_conversation_messages(conversation_id, token)
        if response.get("success") and response.get("messages"):
            messages = response["messages"]
            
            # Convert to the format expected by the chat interface
            conversation_history = []
            for msg in messages:
                conversation_history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp")
                })
            
            st.session_state.conversation_history = conversation_history
            st.session_state.current_session_id = conversation_id
            st.session_state.switch_to_chat = True
            st.rerun()
            
    except Exception as e:
        st.error(f"Error loading conversation: {str(e)}")


def delete_conversation(api_client: APIClient, conversation_id: str, token: str):
    """Delete a conversation."""
    try:
        response = api_client.delete_conversation(conversation_id, token)
        if response.get("success"):
            st.success("Conversation deleted")
            st.rerun()
        else:
            st.error("Failed to delete conversation")
    except Exception as e:
        st.error(f"Error deleting conversation: {str(e)}")
