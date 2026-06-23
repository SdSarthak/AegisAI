"""Unit tests for backend/app/schemas/pagination.py."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.pagination import PaginatedResponse, CursorPaginatedResponse


class _DummyItem(BaseModel):
    """Minimal model for testing generic pagination schemas."""
    id: int
    name: str


class TestPaginatedResponse:
    """Tests for PaginatedResponse[T]."""

    def test_fields_present(self) -> None:
        """PaginatedResponse has all required fields."""
        resp = PaginatedResponse[_DummyItem](
            items=[_DummyItem(id=1, name="alpha")],
            total=42,
            skip=10,
            limit=20,
        )
        assert resp.total == 42
        assert resp.skip == 10
        assert resp.limit == 20
        assert len(resp.items) == 1
        assert resp.items[0].name == "alpha"

    def test_generic_type_preserved(self) -> None:
        """Generic type T is preserved at runtime."""
        items = [_DummyItem(id=i, name=f"item_{i}") for i in range(3)]
        resp = PaginatedResponse[_DummyItem](items=items, total=10, skip=0, limit=3)
        assert all(isinstance(it, _DummyItem) for it in resp.items)

    def test_empty_items(self) -> None:
        """PaginatedResponse handles an empty items list."""
        resp = PaginatedResponse[str](items=[], total=0, skip=0, limit=10)
        assert resp.items == []
        assert resp.total == 0

    def test_serialization_roundtrip(self) -> None:
        """model_dump serialises correctly to dict/JSON."""
        resp = PaginatedResponse[_DummyItem](
            items=[_DummyItem(id=5, name="beta")],
            total=100,
            skip=20,
            limit=10,
        )
        data = resp.model_dump()
        assert data["total"] == 100
        assert data["skip"] == 20
        assert data["limit"] == 10
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "beta"

    def test_large_total_count(self) -> None:
        """Large total counts (e.g. millions) are stored without overflow."""
        resp = PaginatedResponse[str](
            items=[],
            total=10_000_000,
            skip=0,
            limit=100,
        )
        assert resp.total == 10_000_000


class TestCursorPaginatedResponse:
    """Tests for CursorPaginatedResponse[T]."""

    def test_fields_present(self) -> None:
        """CursorPaginatedResponse has all required fields."""
        resp = CursorPaginatedResponse[_DummyItem](
            items=[_DummyItem(id=2, name="gamma")],
            limit=25,
            next_cursor="abc123",
        )
        assert resp.limit == 25
        assert resp.next_cursor == "abc123"
        assert len(resp.items) == 1

    def test_next_cursor_none_default(self) -> None:
        """next_cursor defaults to None when no more pages exist."""
        resp = CursorPaginatedResponse[str](items=[], limit=10)
        assert resp.next_cursor is None
        assert resp.limit == 10

    def test_next_cursor_explicit_none(self) -> None:
        """next_cursor can be explicitly set to None."""
        resp = CursorPaginatedResponse[str](items=[], limit=5, next_cursor=None)
        assert resp.next_cursor is None

    def test_generic_type_preserved(self) -> None:
        """Generic type T is preserved at runtime."""
        items = [_DummyItem(id=i, name=f"cursor_item_{i}") for i in range(2)]
        resp = CursorPaginatedResponse[_DummyItem](items=items, limit=2)
        assert all(isinstance(it, _DummyItem) for it in resp.items)

    def test_serialization_roundtrip(self) -> None:
        """model_dump serialises correctly to dict/JSON."""
        resp = CursorPaginatedResponse[_DummyItem](
            items=[_DummyItem(id=9, name="delta")],
            limit=15,
            next_cursor="xyz789",
        )
        data = resp.model_dump()
        assert data["limit"] == 15
        assert data["next_cursor"] == "xyz789"
        assert len(data["items"]) == 1

    def test_empty_items_with_cursor(self) -> None:
        """Empty items with an explicit cursor is a valid state."""
        resp = CursorPaginatedResponse[str](items=[], limit=50, next_cursor="gone")
        assert resp.items == []
        assert resp.next_cursor == "gone"
