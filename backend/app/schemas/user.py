from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import SubscriptionTier


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None


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
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
