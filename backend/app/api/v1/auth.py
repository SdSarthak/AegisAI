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

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.config import settings
from app.core.rate_limit import DistributedRateLimiter
from app.models.user import User
from app.models.ai_system import AISystem, ComplianceStatus
from app.models.document import Document
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdateSchema,
    Token,
    UserStatsResponse,
    ChangePasswordRequest,
    DashboardLayoutUpdate,
    DashboardLayoutResponse,
)

# Pre-computed bcrypt hash used when the looked-up user is None so that the
# login endpoint always performs a constant-time hash comparison, closing
# the timing side-channel that would otherwise let attackers enumerate valid
# email addresses by measuring response latency.
_DUMMY_HASH = get_password_hash("dummy-timing-safe-placeholder")

_AUTH_LOGIN_RATE_LIMIT_REQUESTS = 5
_AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
_AUTH_REGISTER_RATE_LIMIT_REQUESTS = 3
_AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS = 3600

auth_login_rate_limiter = DistributedRateLimiter(failure_threshold=5, recovery_timeout=30)
auth_register_rate_limiter = DistributedRateLimiter(failure_threshold=5, recovery_timeout=30)

router = APIRouter()
users_router = APIRouter()

DEFAULT_DASHBOARD_LAYOUT = {
    "layout": [
        {"i": "compliance_summary", "x": 0, "y": 0, "w": 2, "h": 2},
        {"i": "risk_distribution", "x": 2, "y": 0, "w": 1, "h": 2},
        {"i": "recent_systems", "x": 0, "y": 2, "w": 3, "h": 2},
        {"i": "deadlines", "x": 3, "y": 0, "w": 1, "h": 2},
    ],
    "hidden": [],
}


def _get_request_ip(request: Request) -> str:
    client = request.client
    return client.host if client and client.host else "unknown"


def clear_auth_rate_limits() -> None:
    """Reset auth rate limit state for tests."""
    auth_login_rate_limiter.clear_local_attempts()
    auth_register_rate_limiter.clear_local_attempts()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new user account."""
    client_ip = _get_request_ip(request)
    limited, retry_after = auth_register_rate_limiter.check_and_consume(
        key=f"auth:register:{client_ip}",
        limit=_AUTH_REGISTER_RATE_LIMIT_REQUESTS,
        window_seconds=_AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        fail_closed=True,
    )
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "field": "general",
                "message": "Too many registration attempts from this IP. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "field": "general",
                    "message": "This email is already registered. Please use a different email or try logging in."
                }
            )

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
    except HTTPException:
        raise
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
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""
    client_ip = _get_request_ip(request)
    login_key = f"auth:login:{form_data.username.lower()}:{client_ip}"
    limited, retry_after = auth_login_rate_limiter.check_and_consume(
        key=login_key,
        limit=_AUTH_LOGIN_RATE_LIMIT_REQUESTS,
        window_seconds=_AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        fail_closed=True,
    )
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "field": "general",
                "message": "Too many login attempts. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )

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


@router.get("/csrf-token", tags=["auth"])
def get_csrf_token():
    """
    Return a fresh CSRF token and set it as an HttpOnly cookie.

    The cookie value is HttpOnly (not readable by JavaScript) so this
    endpoint is safe to call from the browser.  Clients must echo the
    cookie value back in the X-CSRF-Token header on every state-changing
    request (POST / PUT / PATCH / DELETE).
    """
    from fastapi.responses import JSONResponse
    from app.middleware.csrf import make_csrf_response, _generate_token
    token = _generate_token()
    return make_csrf_response(token)


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

@users_router.get(
    "/me/dashboard-layout",
    response_model=DashboardLayoutResponse,
)
def get_dashboard_layout(
    current_user: User = Depends(get_current_user),
):
    return current_user.dashboard_layout or DEFAULT_DASHBOARD_LAYOUT


@users_router.put(
    "/me/dashboard-layout",
    response_model=DashboardLayoutResponse,
)
def update_dashboard_layout(
    payload: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.dashboard_layout = {
        "layout": payload.layout,
        "hidden": payload.hidden,
    }

    current_user = db.merge(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user.dashboard_layout