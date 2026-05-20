import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

scim_auth_scheme = HTTPBearer(auto_error=False)

def verify_scim_token(credentials: HTTPAuthorizationCredentials = Depends(scim_auth_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing SCIM Token")
    if not secrets.compare_digest(credentials.credentials, settings.SCIM_BEARER_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid SCIM Token")
