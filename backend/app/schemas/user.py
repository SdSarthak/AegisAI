
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict
from datetime import datetime
from app.models.user import SubscriptionTier

from app.core.security import validate_password_strength


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=100)

    @field_validator('password')
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
        raise ValueError('Password must be at least 8 characters long.')
    if not re.search(r"\d", value):
        raise ValueError('Password must include at least one number.')
    if not re.search(r"[A-Z]", value):
        raise ValueError('Password must include at least one uppercase letter.')
    if not re.search(r'[!@#$%^&*]', value):
        raise ValueError('Password must include at least one special character (!@#$%^&*).')
    return value


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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)