from pydantic import BaseModel

from app.schemas.pagination import PaginatedResponse


class ItemSchema(BaseModel):
    id: int
    name: str


class TestPaginatedResponseSchema:
    def test_paginated_response_exposes_required_fields(self):
        schema = PaginatedResponse[int].model_json_schema()

        assert set(schema["properties"]) >= {"items", "total", "page", "limit"}
        assert set(schema["required"]) == {"items", "total", "page", "limit"}
        assert schema["properties"]["items"]["type"] == "array"

    def test_items_is_typed_as_a_list(self):
        response = PaginatedResponse[int](
            items=[1, 2, 3],
            total=3,
            page=1,
            limit=10,
        )

        assert isinstance(response.items, list)
        assert response.items == [1, 2, 3]

    def test_serializes_and_deserializes_integer_items(self):
        response = PaginatedResponse[int].model_validate(
            {
                "items": [1, 2],
                "total": 2,
                "page": 1,
                "limit": 10,
            }
        )

        serialized = response.model_dump()
        assert serialized == {
            "items": [1, 2],
            "total": 2,
            "page": 1,
            "limit": 10,
        }

        assert PaginatedResponse[int].model_validate(serialized) == response

    def test_serializes_and_deserializes_string_items(self):
        response = PaginatedResponse[str].model_validate_json(
            '{"items":["alpha","beta"],"total":2,"page":1,"limit":10}'
        )

        assert response.items == ["alpha", "beta"]
        assert response.model_dump() == {
            "items": ["alpha", "beta"],
            "total": 2,
            "page": 1,
            "limit": 10,
        }

    def test_serializes_and_deserializes_model_items(self):
        response = PaginatedResponse[ItemSchema].model_validate(
            {
                "items": [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}],
                "total": 2,
                "page": 1,
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
            "page": 1,
            "limit": 10,
        }

    def test_total_can_exceed_number_of_items(self):
        response = PaginatedResponse[str](
            items=["only-current-page"],
            total=42,
            page=2,
            limit=1,
        )

        assert len(response.items) == 1
        assert response.total == 42
