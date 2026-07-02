"""
Unit tests for backend/app/schemas/pagination.py — CursorPaginatedResponse.

Tests cover:
- Schema exposes required fields (items, limit, next_cursor)
- next_cursor can be null or a non-null string
- items is typed as a list
- Serialization / deserialization round-trip
- Empty items list
"""
from pydantic import BaseModel

from app.schemas.pagination import CursorPaginatedResponse


class ItemSchema(BaseModel):
    id: int
    name: str


class TestCursorPaginatedResponseSchema:
    def test_schema_exposes_required_fields(self):
        """CursorPaginatedResponse must expose items, limit, and next_cursor."""
        schema = CursorPaginatedResponse[int].model_json_schema()
        props = set(schema["properties"])

        assert "items" in props
        assert "limit" in props
        assert "next_cursor" in props

    def test_items_is_list_of_ints(self):
        """items can contain integers."""
        response = CursorPaginatedResponse[int](
            items=[1, 2, 3],
            limit=10,
            next_cursor=None,
        )

        assert isinstance(response.items, list)
        assert response.items == [1, 2, 3]

    def test_next_cursor_null(self):
        """next_cursor may be null when there are no further pages."""
        response = CursorPaginatedResponse[str](
            items=["a", "b"],
            limit=10,
            next_cursor=None,
        )

        assert response.next_cursor is None

    def test_next_cursor_non_null(self):
        """next_cursor contains an opaque cursor string for the next page."""
        response = CursorPaginatedResponse[str](
            items=["c", "d"],
            limit=10,
            next_cursor="eyJpZCI6MTB9",
        )

        assert response.next_cursor == "eyJpZCI6MTB9"

    def test_serializes_and_deserializes_model_items(self):
        """Round-trip: dict -> model -> dict -> model produces the same data."""
        initial = CursorPaginatedResponse[ItemSchema].model_validate(
            {
                "items": [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}],
                "limit": 5,
                "next_cursor": None,
            }
        )

        serialized = initial.model_dump()
        round_tripped = CursorPaginatedResponse[ItemSchema].model_validate(serialized)

        assert round_tripped.items == initial.items
        assert round_tripped.limit == initial.limit
        assert round_tripped.next_cursor == initial.next_cursor

    def test_serializes_and_deserializes_from_json_string(self):
        """CursorPaginatedResponse deserializes correctly from JSON."""
        response = CursorPaginatedResponse[str].model_validate_json(
            '{"items":["alpha","beta"],"limit":20,"next_cursor":"cursor123"}'
        )

        assert response.items == ["alpha", "beta"]
        assert response.limit == 20
        assert response.next_cursor == "cursor123"

    def test_empty_items_list(self):
        """items may be an empty list when no results match."""
        response = CursorPaginatedResponse[str](
            items=[],
            limit=10,
            next_cursor=None,
        )

        assert response.items == []
        assert len(response.items) == 0

    def test_next_cursor_changes_between_pages(self):
        """next_cursor on the second page differs from the first page cursor."""
        first_page = CursorPaginatedResponse[str](
            items=["item-1", "item-2"],
            limit=2,
            next_cursor="page-1-cursor",
        )

        second_page = CursorPaginatedResponse[str](
            items=["item-3"],
            limit=2,
            next_cursor=None,
        )

        assert first_page.next_cursor is not None
        assert second_page.next_cursor is None
        assert first_page.items != second_page.items
