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

from sqlalchemy import func
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
    limited, retry_after = auth_register_rate_limiter.check(
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
        # Record the failed registration attempt so repeated abuse is rate-limited
        auth_register_rate_limiter.record_attempt(
            key=f"auth:register:{client_ip}",
            limit=_AUTH_REGISTER_RATE_LIMIT_REQUESTS,
            window_seconds=_AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        )
        raise
    except Exception:
        db.rollback()
        # Record the failed registration attempt so repeated abuse is rate-limited
        auth_register_rate_limiter.record_attempt(
            key=f"auth:register:{client_ip}",
            limit=_AUTH_REGISTER_RATE_LIMIT_REQUESTS,
            window_seconds=_AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        )
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
        token_version=user.token_version,
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
    current_user.token_version += 1
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
    # Count by risk level using SQL aggregation — never loads individual rows.
    risk_rows = (
        db.query(AISystem.risk_level, func.count(AISystem.id))
        .filter(AISystem.owner_id == current_user.id)
        .group_by(AISystem.risk_level)
        .all()
    )
    risk_breakdown: dict = {
        row[0].value: row[1] for row in risk_rows if row[0] is not None
    }
    total_systems = sum(risk_breakdown.values())

    # Count compliant systems with a separate aggregate query.
    compliant_systems = (
        db.query(func.count(AISystem.id))
        .filter(
            AISystem.owner_id == current_user.id,
            AISystem.compliance_status == ComplianceStatus.COMPLIANT,
        )
        .scalar()
    ) or 0

    total_documents = db.query(Document).filter(Document.owner_id == current_user.id).count()

    return UserStatsResponse(
        total_systems=total_systems,
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
# ── OAuth 2.0 (Google + GitHub) ──────────────────────────────────────────────

from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from fastapi.responses import RedirectResponse

starlette_config = StarletteConfig(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
    "GITHUB_CLIENT_ID": settings.GITHUB_CLIENT_ID,
    "GITHUB_CLIENT_SECRET": settings.GITHUB_CLIENT_SECRET,
})

oauth = OAuth(starlette_config)

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="github",
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


def _get_or_create_oauth_user(db: Session, email: str, full_name: str, provider: str, oauth_id: str, avatar_url: str) -> User:
    """Find existing user by email or create a new OAuth user."""
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=None,
        oauth_provider=provider,
        oauth_id=oauth_id,
        avatar_url=avatar_url,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Google ────────────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback and return JWT."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=400, detail="Google authentication failed.")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google.")

    user = _get_or_create_oauth_user(
        db=db,
        email=user_info["email"],
        full_name=user_info.get("name", ""),
        provider="google",
        oauth_id=user_info["sub"],
        avatar_url=user_info.get("picture", ""),
    )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/oauth/callback#token={access_token}"
    )


# ── GitHub ────────────────────────────────────────────────────────────────────

@router.get("/github")
async def github_login(request: Request):
    """Redirect user to GitHub OAuth consent screen."""
    redirect_uri = str(request.url_for("github_callback"))
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", name="github_callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback and return JWT."""
    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=400, detail="GitHub authentication failed.")

    resp = await oauth.github.get("user", token=token)
    profile = resp.json()

    email = profile.get("email")
    if not email:
        emails_resp = await oauth.github.get("user/emails", token=token)
        emails = emails_resp.json()
        primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
        if not primary:
            raise HTTPException(status_code=400, detail="Could not retrieve verified email from GitHub.")
        email = primary

    user = _get_or_create_oauth_user(
        db=db,
        email=email,
        full_name=profile.get("name") or profile.get("login", ""),
        provider="github",
        oauth_id=str(profile["id"]),
        avatar_url=profile.get("avatar_url", ""),
    )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/oauth/callback#token={access_token}"
    )