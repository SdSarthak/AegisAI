"""
Authentication API — JWT-based user registration, login, and token management.

This module populates two FastAPI routers:
  - ``router``       — mounted at /api/v1/auth  (register, login, me, change-password)
  - ``users_router`` — mounted at /api/v1/users (PATCH /me for profile updates)

Dependencies:
  - python-jose  : JWT creation and verification
  - bcrypt        : password hashing via passlib
  - SQLAlchemy    : ORM session for User persistence
  - pydantic      : request/response schema validation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import re
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.config import settings
from app.models.user import User
from app.models.ai_system import AISystem, ComplianceStatus
from app.models.document import Document
from app.schemas.user import UserCreate, UserResponse, UserUpdateSchema, Token, UserStatsResponse


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
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

router = APIRouter()
users_router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. Please use a different email or try logging in."
        )

    try:
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            company_name=user_data.company_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        # Generic database error handler
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration. Please try again."
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate a user and return an access token."""
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the authenticated user's password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user = db.merge(current_user)
    db.commit()
    return {"message": "Password updated successfully"}


@users_router.patch("/me", response_model=UserResponse)
def update_current_user_info(
    user_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's profile details."""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.company_name is not None:
        current_user.company_name = user_data.company_name

    current_user = db.merge(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@users_router.get("/me/stats", response_model=UserStatsResponse)
def get_current_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return summary statistics for the authenticated user."""
    systems = db.query(AISystem).filter(AISystem.owner_id == current_user.id).all()

    risk_breakdown: dict = {}
    compliant_systems = 0
    for system in systems:
        if system.risk_level:
            key = system.risk_level.value
            risk_breakdown[key] = risk_breakdown.get(key, 0) + 1
        if system.compliance_status == ComplianceStatus.COMPLIANT:
            compliant_systems += 1

    total_documents = db.query(Document).filter(Document.owner_id == current_user.id).count()

    return UserStatsResponse(
        total_systems=len(systems),
        total_documents=total_documents,
        risk_breakdown=risk_breakdown,
        compliant_systems=compliant_systems,
    )
