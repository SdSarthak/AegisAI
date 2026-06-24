from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import get_request_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp

_EXEMPT_PATHS: tuple[str, ...] = (
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
)

_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/badge",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/csrf-token",
)


def _is_exempt(path: str) -> bool:
    if path in _EXEMPT_PATHS:
        return True
    for prefix in _EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class OriginCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: ASGIApp
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        if _is_exempt(request.url.path):
            return await call_next(request)

        origin = request.headers.get("origin")
        if not origin:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Origin header required. Requests without an Origin header are not allowed.",
                    "request_id": get_request_id(),
                },
            )

        return await call_next(request)
