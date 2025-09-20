"""User and profile models."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class EmploymentStatus(str, Enum):
    """Employment status enumeration."""
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"
    STUDENT = "student"


class FilingStatus(str, Enum):
    """Tax filing status enumeration."""
    SINGLE = "single"
    MARRIED_JOINT = "married_joint"
    MARRIED_SEPARATE = "married_separate"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"


class User(BaseModel):
    """User model."""
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    password_hash: Optional[str] = Field(None, description="Hashed password")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # --- Validators (safe, non-breaking) ---
    @validator("email", "name", pre=True)
    def _trim_str(cls, v):
        return v.strip() if isinstance(v, str) else v

    class Config:
        """Pydantic configuration."""
        json_encoders = {datetime: lambda v: v.isoformat()}
        orm_mode = True

    # --- Convenience for DB writes (optional) ---
    def to_db_dict(self) -> Dict[str, Any]:
        d = self.dict()
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        return d


class UserProfile(BaseModel):
    """User profile with tax-related information."""
    user_id: str = Field(..., description="Associated user ID")

    # Personal Information
    employment_status: Optional[EmploymentStatus] = None
    filing_status: Optional[FilingStatus] = None
    annual_income: Optional[float] = None
    dependents: int = Field(default=0)

    # Tax Preferences
    preferred_deductions: List[str] = Field(default_factory=list)
    tax_goals: List[str] = Field(default_factory=list)
    risk_tolerance: str = Field(default="conservative")  # conservative, moderate, aggressive

    # Interaction History
    conversation_count: int = Field(default=0)
    last_interaction: Optional[datetime] = None
    preferred_communication_style: str = Field(default="friendly")

    # Learned Preferences
    frequently_asked_questions: List[str] = Field(default_factory=list)
    common_expenses: List[str] = Field(default_factory=list)
    tax_complexity_level: str = Field(default="beginner")  # beginner, intermediate, advanced

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Validators (safe, non-breaking) ---
    @validator("annual_income", pre=True)
    def _to_float_nonneg(cls, v):
        if v is None or v == "":
            return None
        try:
            fv = float(v)
        except Exception:
            return None
        return max(0.0, fv)

    @validator("dependents", "conversation_count", pre=True)
    def _nonneg_int(cls, v):
        try:
            iv = int(v)
        except Exception:
            iv = 0
        return max(0, iv)

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}
        orm_mode = True

    def to_db_dict(self) -> Dict[str, Any]:
        d = self.dict()
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        if isinstance(d.get("last_interaction"), datetime):
            d["last_interaction"] = d["last_interaction"].isoformat()
        return d


class TaxDocument(BaseModel):
    """Tax document model."""
    id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="Associated user ID")
    document_type: str = Field(..., description="Type of tax document")
    year: int = Field(..., description="Tax year")
    amount: Optional[float] = None
    description: str = Field(..., description="Document description")
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Validators (safe, non-breaking) ---
    @validator("amount", pre=True)
    def _amount_to_float_nonneg(cls, v):
        if v is None or v == "":
            return None
        try:
            fv = float(v)
        except Exception:
            return None
        return max(0.0, fv)

    @validator("description", pre=True)
    def _desc_fallback(cls, v):
        if isinstance(v, str) and v.strip():
            return v.strip()
        return "Document"

    class Config:
        """Pydantic configuration."""
        json_encoders = {datetime: lambda v: v.isoformat()}
        orm_mode = True

    def to_db_dict(self) -> Dict[str, Any]:
        d = self.dict()
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        return d
