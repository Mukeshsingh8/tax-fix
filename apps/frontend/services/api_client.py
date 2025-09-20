"""API client for TaxFix backend communication."""

import requests
import json
from typing import Dict, List, Any, Optional
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from config import API_BASE_URL


class APIClient:
    """Handles all API communication with the TaxFix backend."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def make_request(self, endpoint: str, method: str = "GET", data: Dict = None, token: str = None) -> Dict:
        """Make API request to backend."""
        url = f"{self.base_url}{endpoint}"
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
    
    # Authentication endpoints
    def login(self, email: str, password: str) -> Dict:
        """Login user."""
        return self.make_request("/auth/login", "POST", {
            "email": email,
            "password": password
        })
    
    def register(self, name: str, email: str, password: str) -> Dict:
        """Register user."""
        return self.make_request("/auth/register", "POST", {
            "name": name,
            "email": email,
            "password": password
        })
    
    def logout(self, token: str) -> Dict:
        """Logout user."""
        return self.make_request("/auth/logout", "POST", token=token)
    
    def validate_token(self, token: str) -> Dict:
        """Validate authentication token."""
        return self.make_request(f"/auth/me?token={token}", "GET")
    
    # Chat endpoints
    def send_message(self, message: str, session_id: str, token: str) -> Dict:
        """Send message to chat."""
        return self.make_request("/chat/message", "POST", {
            "message": message,  # Fixed: backend expects 'message', not 'content'
            "session_id": session_id
        }, token=token)
    
    def send_message_streaming(self, message: str, session_id: str, token: str):
        """Send message with streaming response."""
        url = f"{self.base_url}/chat/message/stream"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            with requests.post(
                url,
                json={
                    "message": message,
                    "session_id": session_id,
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
                            parsed = json.loads(data)
                            delta = parsed.get("delta", "")
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
    
    # Profile endpoints
    def get_user_profile(self, token: str) -> Dict:
        """Get user profile."""
        return self.make_request("/user/profile", "GET", token=token)
    
    def create_user_profile(self, profile_data: Dict, token: str) -> Dict:
        """Create user profile."""
        return self.make_request("/user/profile", "POST", profile_data, token=token)
    
    def update_user_profile(self, profile_data: Dict, token: str) -> Dict:
        """Update user profile."""
        return self.make_request("/user/profile", "PUT", profile_data, token=token)
    
    # Conversation endpoints
    def get_conversations(self, token: str) -> Dict:
        """Get user conversations."""
        return self.make_request("/user/conversations", "GET", token=token)
    
    def get_conversation_messages(self, conversation_id: str, token: str) -> Dict:
        """Get messages from a conversation."""
        return self.make_request(f"/conversation/{conversation_id}/messages", "GET", token=token)
    
    def delete_conversation(self, conversation_id: str, token: str) -> Dict:
        """Delete a conversation."""
        return self.make_request(f"/conversation/{conversation_id}", "DELETE", token=token)
    
    # Dashboard endpoints
    def get_dashboard_data(self, token: str) -> Dict:
        """Get comprehensive dashboard data."""
        return self.make_request("/user/dashboard-data", "GET", token=token)
    
    def get_expenses(self, token: str) -> Dict:
        """Get user expenses."""
        return self.make_request("/user/expenses", "GET", token=token)
