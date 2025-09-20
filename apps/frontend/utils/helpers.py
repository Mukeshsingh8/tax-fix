"""Helper utilities for TaxFix Frontend."""

import re
import time
import uuid
from typing import Iterator, List, Dict, Any
from datetime import datetime


class MarkdownProcessor:
    """Handles markdown processing for streaming responses."""
    
    @staticmethod
    def clean_for_streaming(text: str) -> str:
        """Clean markdown text for streaming display."""
        # Remove incomplete markdown links
        text = re.sub(r'\[([^\]]*?)$', r'\1', text)
        
        # Handle incomplete code blocks
        if text.count('```') % 2 == 1:
            # Odd number of backticks, close the block
            text += '\n```'
        
        # Clean up incomplete bold/italic
        text = re.sub(r'\*\*([^*]+)$', r'\1', text)
        text = re.sub(r'\*([^*]+)$', r'\1', text)
        
        return text
    
    @staticmethod
    def is_complete_block(text: str) -> bool:
        """Check if markdown block is complete."""
        # Check for complete code blocks
        if '```' in text:
            return text.count('```') % 2 == 0
        
        # Check for complete tables
        if '|' in text:
            lines = text.split('\n')
            table_lines = [line for line in lines if '|' in line]
            if table_lines:
                return len(table_lines) >= 2  # Header + separator minimum
        
        return True
    
    @staticmethod
    def finalize(text: str) -> str:
        """Finalize markdown text."""
        # Ensure proper spacing
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up any remaining artifacts
        text = text.strip()
        
        return text


class StreamingHelper:
    """Handles streaming response processing."""
    
    @staticmethod
    def block_stream(token_iter: Iterator[str], buffer_size: int = 150):
        """Process streaming tokens in blocks."""
        buffer = ""
        last_sent = 0
        processor = MarkdownProcessor()
        
        def should_flush(b: str) -> bool:
            return (
                len(b) - last_sent >= buffer_size or
                b.endswith('\n\n') or
                b.endswith('.') or
                b.endswith('!') or
                b.endswith('?') or
                '```' in b[-10:]
            )
        
        for token in token_iter:
            if not token:
                continue
                
            buffer += token
            
            if should_flush(buffer) and processor.is_complete_block(buffer):
                piece = buffer[last_sent:]
                if piece.strip():
                    yield processor.clean_for_streaming(piece)
                    last_sent = len(buffer)
        
        # Send remaining buffer
        if last_sent < len(buffer):
            piece = buffer[last_sent:]
            if piece.strip():
                yield processor.finalize(piece)
    
    @staticmethod
    def delta_stream(chunks_iter: Iterator[str]):
        """Process streaming chunks with delta updates."""
        buffer = ""
        last_sent = 0
        
        for chunk in chunks_iter:
            if not chunk:
                continue
            buffer += chunk
            
            # Send new content
            piece = buffer[last_sent:]
            if not piece:
                continue
            yield piece
            last_sent = len(buffer)


class SessionHelper:
    """Handles session management utilities."""
    
    @staticmethod
    def generate_session_id(user_id: str) -> str:
        """Generate a unique session ID."""
        return f"session_{user_id}_{int(time.time())}"
    
    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """Format timestamp for display."""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")


class DataFormatter:
    """Handles data formatting utilities."""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format currency amount."""
        return f"€{amount:,.2f}"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage value."""
        return f"{value:.1f}%"
    
    @staticmethod
    def get_icon_for_status(status: str) -> str:
        """Get icon for employment status."""
        icons = {
            "employed": "💼",
            "self_employed": "🏢", 
            "unemployed": "🔍",
            "retired": "🏖️",
            "student": "🎓"
        }
        return icons.get(status.lower(), "❓")
    
    @staticmethod
    def get_icon_for_risk(risk: str) -> str:
        """Get icon for risk tolerance."""
        icons = {
            "conservative": "🛡️",
            "moderate": "⚖️",
            "aggressive": "🚀"
        }
        return icons.get(risk.lower(), "❓")
    
    @staticmethod
    def get_dependents_icon(count: int) -> str:
        """Get icon for dependents count."""
        if count == 0:
            return "👤"
        elif count == 1:
            return "👨‍👧"
        elif count == 2:
            return "👨‍👩‍👧‍👦"
        else:
            return "👨‍👩‍👧‍👦+"


class ValidationHelper:
    """Handles form validation utilities."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input."""
        # Remove potential script tags and harmful content
        text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        return text.strip()
