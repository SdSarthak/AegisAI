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

_auth_login_failures_by_key: dict[str, deque[datetime]] = defaultdict(deque)
_auth_registration_attempts_by_ip: dict[str, deque[datetime]] = defaultdict(deque)
_auth_rate_limit_lock = Lock()

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
<<<<<<< HEAD
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
        url=f"{settings.FRONTEND_URL}/oauth/callback?token={access_token}"
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
        url=f"{settings.FRONTEND_URL}/oauth/callback?token={access_token}"
    )


# ── Dashboard Layout ──────────────────────────────────────────────────────────

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
=======

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
>>>>>>> upstream/main
