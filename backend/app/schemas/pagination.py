from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for list endpoints."""
    items: List[T]
    total: int
    page: int
    limit: int
