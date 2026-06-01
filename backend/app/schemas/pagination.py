from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for list endpoints."""
    items: List[T]
    total: int
    skip: int
    limit: int


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based pagination response wrapper for scalable list endpoints."""

    items: List[T]
    limit: int
    next_cursor: str | None = None

