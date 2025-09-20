"""Pydantic models for API requests and responses."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    suggested_actions: list = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RegisterRequest(BaseModel):
    """Registration request model."""
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    annual_income: Optional[float] = None
    employment_status: Optional[str] = None
    filing_status: Optional[str] = None
    dependents: int = 0
    conversation_count: int = 0
    last_interaction: Optional[datetime] = None


class CreateProfileRequest(BaseModel):
    """Profile creation request model."""
    employment_status: str = Field(..., description="Employment status")
    filing_status: str = Field(..., description="Filing status")
    annual_income: float = Field(..., description="Annual income")
    dependents: int = Field(default=0, description="Number of dependents")
    preferred_deductions: list = Field(default_factory=list, description="Preferred deductions")
    tax_goals: list = Field(default_factory=list, description="Tax goals")
    risk_tolerance: str = Field(default="conservative", description="Risk tolerance")
    preferred_communication_style: str = Field(default="friendly", description="Communication style")
    tax_complexity_level: str = Field(default="beginner", description="Tax complexity level")
