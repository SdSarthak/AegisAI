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

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

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
from app.models.user import User
from app.models.ai_system import AISystem, ComplianceStatus
from app.models.document import Document
from app.schemas.user import UserCreate, UserResponse, UserUpdateSchema, Token, UserStatsResponse, ChangePasswordRequest, DashboardLayoutUpdate

# Pre-computed bcrypt hash used when the looked-up user is None so that the
# login endpoint always performs a constant-time hash comparison, closing
# the timing side-channel that would otherwise let attackers enumerate valid
# email addresses by measuring response latency.
_DUMMY_HASH = get_password_hash("dummy-timing-safe-placeholder")

_AUTH_LOGIN_RATE_LIMIT_REQUESTS = 5
_AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
_AUTH_REGISTER_RATE_LIMIT_REQUESTS = 3
_AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS = 3600

_auth_login_failures_by_key: dict[str, deque[datetime]] = defaultdict(deque)
_auth_registration_attempts_by_ip: dict[str, deque[datetime]] = defaultdict(deque)
_auth_rate_limit_lock = Lock()

router = APIRouter()
users_router = APIRouter()


def _get_request_ip(request: Request) -> str:
    client = request.client
    return client.host if client and client.host else "unknown"


def _prune_attempts(
    attempts: deque[datetime],
    window_seconds: int,
    now: datetime,
) -> None:
    cutoff = now - timedelta(seconds=window_seconds)
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()


def _retry_after_seconds(
    attempts: deque[datetime],
    window_seconds: int,
    now: datetime,
) -> int:
    if not attempts:
        return window_seconds

    oldest = attempts[0]
    return max(1, int((window_seconds - (now - oldest).total_seconds()) + 0.999))


def _is_rate_limited(
    store: dict[str, deque[datetime]],
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    now = datetime.now(timezone.utc)
    with _auth_rate_limit_lock:
        attempts = store[key]
        _prune_attempts(attempts, window_seconds, now)
        if len(attempts) >= limit:
            return True, _retry_after_seconds(attempts, window_seconds, now)
        return False, 0


def _record_attempt(
    store: dict[str, deque[datetime]],
    key: str,
    window_seconds: int,
) -> None:
    now = datetime.now(timezone.utc)
    with _auth_rate_limit_lock:
        attempts = store[key]
        _prune_attempts(attempts, window_seconds, now)
        attempts.append(now)


def clear_auth_rate_limits() -> None:
    """Reset in-memory auth rate limit state for tests."""
    with _auth_rate_limit_lock:
        _auth_login_failures_by_key.clear()
        _auth_registration_attempts_by_ip.clear()


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
    limited, retry_after = _is_rate_limited(
        _auth_registration_attempts_by_ip,
        client_ip,
        _AUTH_REGISTER_RATE_LIMIT_REQUESTS,
        _AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
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
    finally:
        _record_attempt(
            _auth_registration_attempts_by_ip,
            client_ip,
            _AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        )


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""
    client_ip = _get_request_ip(request)
    login_key = f"{form_data.username.lower()}:{client_ip}"
    limited, retry_after = _is_rate_limited(
        _auth_login_failures_by_key,
        login_key,
        _AUTH_LOGIN_RATE_LIMIT_REQUESTS,
        _AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
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
        _record_attempt(
            _auth_login_failures_by_key,
            login_key,
            _AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
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


@users_router.get("/me/dashboard-layout")
def get_dashboard_layout(
    current_user: User = Depends(get_current_user),
):
    """Return the user's saved dashboard layout."""
    return {
        "layout": current_user.dashboard_layout.get("layout", []) if current_user.dashboard_layout else [],
        "hidden": current_user.dashboard_layout.get("hidden", []) if current_user.dashboard_layout else [],
    }


@users_router.put("/me/dashboard-layout")
def update_dashboard_layout(
    body: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save the user's dashboard layout configuration."""
    current_user.dashboard_layout = {
        "layout": body.layout,
        "hidden": body.hidden,
    }
    current_user = db.merge(current_user)
    db.commit()
    return {"status": "ok"}
