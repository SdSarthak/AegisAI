from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import user_id_ctx
from app.core.database import get_db

from fastapi.security import OAuth2PasswordBearer
from fastapi import Header
from app.models.api_key import ApiKey
from app.models.user import User
from app.core.security import hash_api_key

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False
)

if TYPE_CHECKING:
    from app.models.user import User  # Prevent circular imports during runtime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _get_credentials_exception() -> HTTPException:
    """Helper to return a standardized 401 Unauthorized exception."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version."""
    if len(plain_password.encode("utf-8")) > 72:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Securely hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with an expiration payload."""
    to_encode = data.copy()
    
    # Use timezone-aware UTC datetime to prevent standard library deprecation warnings
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token, returning the payload safely."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JWTError:
        raise _get_credentials_exception()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> "User":
    """Get authenticated user from JWT or API key."""

    from app.models.user import User

    # API KEY AUTH
    if x_api_key:
        api_key = (
            db.query(ApiKey)
            .filter(
                ApiKey.key_hash == hash_api_key(x_api_key),
                ApiKey.revoked == False,
            )
            .first()
        )

        if not api_key:
            raise get_credentials_exception()

        user = db.query(User).filter(User.id == api_key.user_id).first()

        if not user:
            raise get_credentials_exception()

        user_id_ctx.set(user.id)
        return user

    # JWT AUTH
    if not token:
        raise get_credentials_exception()

    payload = decode_token(token)
    user_id_str: Optional[str] = payload.get("sub")

    if not user_id_str:
        raise get_credentials_exception()

    try:
        user_id = int(user_id_str)

    except (ValueError, TypeError):
        raise get_credentials_exception()

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise get_credentials_exception()

    user_id_ctx.set(user.id)

    return user