from pydantic import BaseModel

from app.schemas.pagination import PaginatedResponse, CursorPaginatedResponse


class ItemSchema(BaseModel):
    id: int
    name: str


class TestPaginatedResponseSchema:
    def test_paginated_response_exposes_required_fields(self):
        schema = PaginatedResponse[int].model_json_schema()

        assert set(schema["properties"]) >= {"items", "total", "skip", "limit"}
        assert set(schema["required"]) == {"items", "total", "skip", "limit"}
        assert schema["properties"]["items"]["type"] == "array"

    def test_items_is_typed_as_a_list(self):
        response = PaginatedResponse[int](
            items=[1, 2, 3],
            total=3,
            skip=0,
            limit=10,
        )

        assert isinstance(response.items, list)
        assert response.items == [1, 2, 3]

    def test_serializes_and_deserializes_integer_items(self):
        response = PaginatedResponse[int].model_validate(
            {
                "items": [1, 2],
                "total": 2,
                "skip": 0,
                "limit": 10,
            }
        )

        serialized = response.model_dump()
        assert serialized == {
            "items": [1, 2],
            "total": 2,
            "skip": 0,
            "limit": 10,
        }

        assert PaginatedResponse[int].model_validate(serialized) == response

    def test_serializes_and_deserializes_string_items(self):
        response = PaginatedResponse[str].model_validate_json(
            '{"items":["alpha","beta"],"total":2,"skip":0,"limit":10}'
        )

        assert response.items == ["alpha", "beta"]
        assert response.model_dump() == {
            "items": ["alpha", "beta"],
            "total": 2,
            "skip": 0,
            "limit": 10,
        }

    def test_serializes_and_deserializes_model_items(self):
        response = PaginatedResponse[ItemSchema].model_validate(
            {
                "items": [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}],
                "total": 2,
                "skip": 0,
                "limit": 10,
            }
        )

        assert response.items == [
            ItemSchema(id=1, name="First"),
            ItemSchema(id=2, name="Second"),
        ]
        assert response.model_dump() == {
            "items": [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}],
            "total": 2,
            "skip": 0,
            "limit": 10,
        }

    def test_total_can_exceed_number_of_items(self):
        response = PaginatedResponse[str](
            items=["only-current-page"],
            total=42,
            skip=10,
            limit=1,
        )

        assert len(response.items) == 1
        assert response.total == 42


class TestCursorPaginatedResponseSchema:
    def test_cursor_paginated_response_exposes_required_fields(self):
        schema = CursorPaginatedResponse[int].model_json_schema()
        props = set(schema["properties"])
        assert "items" in props
        assert "limit" in props
        assert "next_cursor" in props

    def test_items_is_typed_as_a_list(self):
        response = CursorPaginatedResponse[str](
            items=["alpha", "beta"],
            limit=10,
            next_cursor=None,
        )
        assert isinstance(response.items, list)
        assert response.items == ["alpha", "beta"]

    def test_next_cursor_is_nullable(self):
        # No cursor means no more pages
        response = CursorPaginatedResponse[str].model_validate(
            {"items": ["a"], "limit": 10, "next_cursor": None}
        )
        assert response.next_cursor is None

    def test_next_cursor_accepts_string(self):
        response = CursorPaginatedResponse[str].model_validate(
            {"items": ["a"], "limit": 10, "next_cursor": "abc123"}
        )
        assert response.next_cursor == "abc123"

    def test_serializes_and_deserializes_with_cursor(self):
        response = CursorPaginatedResponse[dict].model_validate({
            "items": [{"id": 1}, {"id": 2}],
            "limit": 2,
            "next_cursor": "page-2-token",
        })
        serialized = response.model_dump()
        assert serialized["next_cursor"] == "page-2-token"
        assert len(serialized["items"]) == 2
        assert CursorPaginatedResponse[dict].model_validate(serialized) == response

    def test_serializes_with_no_next_cursor(self):
        response = CursorPaginatedResponse[int](
            items=[1, 2, 3],
            limit=10,
            next_cursor=None,
        )
        assert response.model_dump()["next_cursor"] is None

    def test_limit_field_present(self):
        response = CursorPaginatedResponse[str](
            items=[],
            limit=25,
            next_cursor=None,
        )
        assert response.limit == 25

    def test_empty_items_list_valid(self):
        response = CursorPaginatedResponse[str].model_validate(
            {"items": [], "limit": 10, "next_cursor": None}
        )
        assert response.items == []
