"""
Auth API — JWT-Based Authentication & User Management
======================================================

This module populates the FastAPI authentication router with endpoints
for user registration, login, and retrieving the current user profile.
It forms the core of the AegisAI identity and access management layer.

Router
------
All routes are registered under the /auth prefix via FastAPI's APIRouter.

Endpoints
---------
POST /auth/register
    Accepts user credentials (email, password, full name, company name)
    and creates a new account. Passwords are hashed using bcrypt before
    being persisted to the database via SQLAlchemy.

POST /auth/login
    Validates credentials against the database and issues a signed JWT
    access token using python-jose. Accepts OAuth2PasswordRequestForm.

GET /auth/me
    Returns the profile of the currently authenticated user, resolved
    via the Bearer token in the Authorization header.

Dependencies
------------
- python-jose  : JWT creation, signing, and validation (via create_access_token)
- bcrypt       : Secure password hashing and verification
- SQLAlchemy   : ORM-based database access for user persistence
- FastAPI      : Routing, dependency injection, and request handling

Notes
-----
- Token expiry and secret settings are sourced from app.core.config.
- No functional code changes — documentation only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company_name=user_data.company_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user
