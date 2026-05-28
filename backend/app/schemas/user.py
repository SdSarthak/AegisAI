from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict
from datetime import datetime
import re
from app.models.user import SubscriptionTier


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Enforce password strength requirements."""
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r'[A-Z]', v):
            errors.append("at least one uppercase letter")
        if not re.search(r'\d', v):
            errors.append("at least one digit")
        if not re.search(r'[!@#$%^&*]', v):
            errors.append("at least one special character (!@#$%^&*)")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=100)
    onboarding_completed: Optional[bool] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserStatsResponse(BaseModel):
    total_systems: int
    total_documents: int
    risk_breakdown: Dict[str, int]
    compliant_systems: int