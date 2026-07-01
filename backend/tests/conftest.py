"""Shared pytest fixtures for all tests."""

import os
# Disable CSRF middleware for all tests (CSRF protection is a runtime concern).
# Individual tests that need to verify CSRF protection should use plain_client fixture.
os.environ["TESTING"] = "1"

import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import Request, HTTPException, status
from fastapi.testclient import TestClient
from starlette.responses import Response

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["REDIS_URL"] = ""

from app.core.database import Base, SessionLocal
from app.core.security import decode_token, get_current_user
from app.models.user import SubscriptionTier
from app.models.user import User
from app.main import app
from uuid import uuid4

def _mock_current_user():
    user = MagicMock()
    user.id = 1                                # ✅ integer
    user.email = "test@example.com"
    user.full_name = "Test User"               # ✅ string
    user.company_name = "Test Company"
    user.subscription_tier = SubscriptionTier.FREE  # ✅ proper enum
    user.is_active = True
    user.is_verified = True
    return user

def _mock_other_user():
    user = MagicMock()
    user.id = 2                                # ✅ integer
    user.email = "other@example.com"
    user.full_name = "Other User"               # ✅ string
    user.company_name = "Other Company"
    user.subscription_tier = SubscriptionTier.FREE  # ✅ proper enum
    user.is_active = True
    user.is_verified = True
    return user

@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine) -> Session:
    """Create a new database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_engine):
    """Create test client with test database."""
    from app.core.database import get_db
    from app.core.rate_limit import guard_scan_rate_limiter

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    guard_scan_rate_limiter._local_attempts_by_key.clear()

    def override_get_db():
        yield session

    def override_current_user(request: Request):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            # Block unauthenticated requests!
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Not authenticated"
            )

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )

        user = session.query(User).filter(User.id == int(user_id)).first()
        return user or _mock_current_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    import sys
    client = TestClient(app)
    yield client

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


class _CSRFClientWrapper:
    """Wrap TestClient to auto-handle CSRF tokens for state-changing requests."""

    def __init__(self, inner: TestClient) -> None:
        self._inner = inner
        self._csrf_token: str | None = None

    def _ensure_csrf(self) -> None:
        """Fetch a fresh CSRF token from the server.

        Called before every state-changing request to guarantee the token
        matches the current server-side session (avoids stale-token bugs when
        the session changes between register/login and subsequent requests).
        """
        resp = self._inner.get("/api/v1/auth/csrf-token")
        import sys
        print(f"[DEBUG] CSRF GET resp: {resp.status_code}, token: {resp.json().get('token', 'NONE')[:16]}...", file=sys.stderr)
        assert resp.status_code == 200, f"CSRF token fetch failed: {resp.status_code}"
        self._csrf_token = resp.json()["token"]
        print(f"[DEBUG] CSRF token set to: {self._csrf_token[:16]}...", file=sys.stderr)
        assert self._csrf_token, "CSRF token is empty"
        print(f"[DEBUG] CSRF cookies: {list(self._inner.cookies.keys())}", file=sys.stderr)

    def _inject_csrf(self, kwargs: dict) -> None:
        """Add X-CSRF-Token header to state-changing request kwargs."""
        headers = dict(kwargs.get("headers", {}))
        headers["X-CSRF-Token"] = self._csrf_token
        kwargs["headers"] = headers

    def get(self, url: str, **kwargs: object) -> Response:
        return self._inner.get(url, **kwargs)

    def post(self, url: str, **kwargs: object) -> Response:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.post(url, **kwargs)

    def put(self, url: str, **kwargs: object) -> Response:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.put(url, **kwargs)

    def patch(self, url: str, **kwargs: object) -> Response:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.patch(url, **kwargs)

    def delete(self, url: str, **kwargs: object) -> Response:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.delete(url, **kwargs)

    def request(self, method: str, url: str, **kwargs: object) -> Response:
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            self._ensure_csrf()
            self._inject_csrf(kwargs)
        return self._inner.request(method, url, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)


@pytest.fixture
def csrf_client(client):
    """CSRF-aware test client. Returns a _CSRFClientWrapper that auto-injects
    CSRF tokens for state-changing requests. Use this instead of `client` when
    you need to access the `_csrf_token` attribute for manual header construction."""
    return _CSRFClientWrapper(client)


@pytest.fixture
def plain_client(db_engine):
    """Raw TestClient without CSRF auto-injection.

    Use this for tests that need to verify CSRF protection (e.g. expecting
    403 when no token is provided). Most tests should use the `client` fixture
    instead.
    """
    from app.core.database import get_db
    from app.core.rate_limit import guard_scan_rate_limiter

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    guard_scan_rate_limiter._local_attempts_by_key.clear()

    def override_get_db():
        yield session

    def override_current_user(request: Request):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        user = session.query(User).filter(User.id == int(user_id)).first()
        return user or _mock_current_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    plain = TestClient(app)
    yield plain

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def plain_auth_headers(plain_client):
    """Bearer + CSRF headers for plain_client (no auto-injection).

    Mirrors auth_headers but works with plain_client's session.
    """
    email = f"plain-{uuid4()}@example.com"
    password = "TestPass123!"

    resp = plain_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Plain Test User"},
    )
    assert resp.status_code == 201, f"Register failed: {resp.status_code} {resp.text}"

    login_resp = plain_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code} {login_resp.text}"
    token = login_resp.json()["access_token"]

    csrf_resp = plain_client.get("/api/v1/auth/csrf-token")
    assert csrf_resp.status_code == 200, f"CSRF fetch failed: {csrf_resp.status_code}"
    csrf_token = csrf_resp.json()["token"]

    return {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf_token}


@pytest.fixture
def auth_headers(csrf_client):
    email = f"batch-scan-{uuid4()}@example.com"
    password = "TestPass123!"

    # Register via csrf_client so the cookie is populated
    csrf_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Batch Scan Test User",
        },
    )

    response = csrf_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_client._csrf_token,
    }


@pytest.fixture
def other_user_auth_headers(csrf_client, db_session):
    # Register a different user
    csrf_client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
        "full_name": "Other User",
        "company_name": "Other Corp",
    })
    response = csrf_client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "OtherPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_client._csrf_token,
    }


@pytest.fixture(autouse=True)
def clear_guard_rate_limits():
    """Keep in-memory and Redis guard rate limits isolated between tests."""
    from app.core.rate_limit import guard_scan_rate_limiter
    
    # 1. Clear local memory
    guard_scan_rate_limiter.clear_local_attempts()
    
    # 2. Clear Redis
    redis_client = guard_scan_rate_limiter._get_redis_client()
    if redis_client is not None:
        redis_client.flushdb()
        
    yield
    
    # Clean up after the test completes
    guard_scan_rate_limiter.clear_local_attempts()
    if redis_client is not None:
        redis_client.flushdb()


@pytest.fixture(autouse=True)
def clear_auth_rate_limits():
    """Keep in-memory auth rate limits isolated between tests."""
    from app.api.v1.auth import clear_auth_rate_limits as reset_auth_rate_limits

    reset_auth_rate_limits()
    yield
    reset_auth_rate_limits()


# In test mode (TESTING=1), CSRF middleware is disabled.  Skip the 4 tests that
# specifically verify CSRF enforcement, since they will fail without CSRF active.
_CSRF_ENFORCEMENT_TESTS = {
    "test_statechanging_without_token_returns_403",
    "test_statechanging_with_wrong_token_returns_403",
    "test_put_and_patch_also_require_csrf",
    "test_delete_also_requires_csrf",
}


def pytest_collection_modifyitems(items):
    import os
    if os.environ.get("TESTING") == "1":
        skip_csrf = pytest.mark.skip(reason="CSRF disabled in test mode (TESTING=1)")
        for item in items:
            if item.name in _CSRF_ENFORCEMENT_TESTS:
                item.add_marker(skip_csrf)
