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

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, APIKeyHeader
import re
import secrets
import hashlib

from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from datetime import timedelta, datetime

from app.core.database import get_db
from app.core.security import (
    validate_password_strength,
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.config import settings
from app.models.user import User
from app.models.ai_system import AISystem, ComplianceStatus
from app.models.document import Document
from app.models.api_key import ApiKey

from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdateSchema,
    Token,
    UserStatsResponse,
    ChangePasswordRequest,
)

from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyGeneratedResponse,
    ApiKeyRevokeResponse,
)

# Pre-computed bcrypt hash used when the looked-up user is None so that the
# login endpoint always performs a constant-time hash comparison, closing
# the timing side-channel that would otherwise let attackers enumerate valid
# email addresses by measuring response latency.
_DUMMY_HASH = get_password_hash("dummy-timing-safe-placeholder")

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
            detail={
                "field": "general",
                "message": "This email is already registered. Please use a different email or try logging in."
            }
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
            detail={
                "field": "general",
                "message": "An error occurred during registration. Please try again."
            }
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate a user and return an access token."""
    user = db.query(User).filter(User.email == form_data.username).first()

    # Always run a constant-time bcrypt comparison regardless of whether the
    # user exists.  Without this, an attacker can distinguish "user not found"
    # (fast — no hash) from "wrong password" (slow — bcrypt verify) by
    # measuring response latency.
    hashed = user.hashed_password if user else _DUMMY_HASH
    password_ok = verify_password(form_data.password, hashed)

    if not user or not user.is_active or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "field": "general",
                "message": "Invalid email or password"
            },
            headers={"WWW-Authenticate": "Bearer"},
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
            detail={
                "field": "general",
                "message": "Current password is incorrect"
            },
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

    if user_data.onboarding_completed is not None:
        current_user.onboarding_completed = user_data.onboarding_completed

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
    total_systems = (
        db.query(AISystem)
        .filter(AISystem.owner_id == current_user.id)
        .count()
    )

    total_documents = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .count()
    )

    systems = (
        db.query(AISystem)
        .filter(AISystem.owner_id == current_user.id)
        .all()
    )

    risk_breakdown = {}
    compliant_systems = 0

    for system in systems:
        risk_level = (
            system.risk_level.value
            if hasattr(system.risk_level, "value")
            else str(system.risk_level)
        )

        risk_breakdown[risk_level] = (
            risk_breakdown.get(risk_level, 0) + 1
        )

        if system.compliance_status == ComplianceStatus.COMPLIANT:
            compliant_systems += 1

    return UserStatsResponse(
        total_systems=total_systems,
        total_documents=total_documents,
        risk_breakdown=risk_breakdown,
        compliant_systems=compliant_systems,
    )


@router.post(
    "/api-keys",
    response_model=ApiKeyGeneratedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_key = secrets.token_urlsafe(32)

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=current_user.id,
        name=payload.name,
        key_hash=key_hash,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyGeneratedResponse(
        api_key=raw_key,
        name=api_key.name,
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_keys = (
        db.query(ApiKey)
        .filter(
            ApiKey.user_id == current_user.id,
            ApiKey.revoked == False,
        )
        .all()
    )

    return api_keys


@router.delete(
    "/api-keys/{api_key_id}",
    response_model=ApiKeyRevokeResponse,
)
def revoke_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.id == api_key_id,
            ApiKey.user_id == current_user.id,
            ApiKey.revoked == False,
        )
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.revoked = True
    api_key.revoked_at = datetime.utcnow()

    db.commit()
    db.refresh(api_key)

    return ApiKeyRevokeResponse(
        message="API key revoked successfully"
    )
