from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
import re

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import user_id_ctx
from app.core.database import get_db

if TYPE_CHECKING:
    from app.models.user import User  # Prevent circular imports during runtime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def _get_credentials_exception() -> HTTPException:
    """Build a standardized 401 Unauthorized exception."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"field": "general", "message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def validate_password_strength(password: str) -> str:
    """Validate that a password meets the project strength policy.

    Args:
        password: Plain-text password to validate.

    Returns:
        The original password when it passes all checks.

    Raises:
        ValueError: If the password is too short or missing required
            character classes.
    """
    errors = []
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("at least one uppercase letter")
    if not re.search(r'\d', password):
        errors.append("at least one digit")
    if not re.search(r'[!@#$%^&*]', password):
        errors.append("at least one special character (!@#$%^&*)")
    if errors:
        raise ValueError("Password must contain: " + ", ".join(errors))
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version.

    Args:
        plain_password: Candidate password to verify.
        hashed_password: Stored bcrypt hash to compare against.

    Returns:
        True when the password matches and is safe to verify.
    """
    if len(plain_password.encode("utf-8")) > 72:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Securely hash a password using bcrypt.

    Args:
        password: Plain-text password to hash.

    Returns:
        A bcrypt password hash string.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with an expiration payload.

    Args:
        data: Token claims to encode.
        expires_delta: Optional custom lifetime for the token.

    Returns:
        A signed JWT access token.
    """
    to_encode = data.copy()
    
    # Use timezone-aware UTC datetime to prevent standard library deprecation warnings
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and strictly validate a JWT token payload.

    Args:
        token: Encoded JWT string to decode.

    Returns:
        The validated token payload.

    Raises:
        HTTPException: If the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "require_sub": True,
                "require_exp": True,
                "require_iat": True,
            },
        )

        # Validate required claims
        sub = payload.get("sub")
        if not sub or not isinstance(sub, str):
            raise _get_credentials_exception()

        # Validate optional timing claims format if present
        for claim in ("iat", "nbf", "exp"):
            value = payload.get(claim)
            if value is not None and not isinstance(value, (int, float)):
                raise _get_credentials_exception()

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"field": "general", "message": "Token has expired. Please log in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JWTError:
        raise _get_credentials_exception()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> "User":
    """Dependency to get the current authenticated user from a JWT.

    Args:
        token: OAuth2 bearer token extracted from the request.
        db: Active database session.

    Returns:
        The authenticated User ORM object.

    Raises:
        HTTPException: If the token is invalid or the user cannot be loaded.
    """
    from app.models.user import User  # Local import to avoid circular dependencies

    payload = decode_token(token)
    user_id_str: Optional[str] = payload.get("sub")

    if not user_id_str:
        raise _get_credentials_exception()

    # Defensively handle malformed or non-integer 'sub' claims
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise _get_credentials_exception()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Standardized to 401 generic failure instead of a distinct "User not found" 401
        # to prevent user enumeration attacks via valid-but-orphaned tokens.
        raise _get_credentials_exception()

    # Bind to the request context so every downstream log line (and the
    # access log emitted by RequestContextMiddleware) carries user_id.
    user_id_ctx.set(user.id)

    return user
