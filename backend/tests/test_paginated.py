from pydantic import BaseModel
from app.schemas.pagination import PaginatedResponse


class DummyItem(BaseModel):
    id: int
    name: str


def test_paginated_response_fields_present():
    response = PaginatedResponse[DummyItem](
        items=[DummyItem(id=1, name="Test")],
        total=10,
        page=1,
        limit=5,
    )

    assert response.items is not None
    assert response.total == 10
    assert response.page == 1
    assert response.limit == 5


def test_paginated_response_items_is_list():
    response = PaginatedResponse[DummyItem](
        items=[DummyItem(id=1, name="Test")],
        total=1,
        page=1,
        limit=10,
    )

    assert isinstance(response.items, list)


def test_paginated_response_serialization():
    response = PaginatedResponse[DummyItem](
        items=[DummyItem(id=1, name="Test")],
        total=1,
        page=1,
        limit=10,
    )

    data = response.model_dump()

    assert data["items"][0]["id"] == 1
    assert data["items"][0]["name"] == "Test"


def test_paginated_response_deserialization():
    data = {
        "items": [{"id": 1, "name": "Test"}],
        "total": 5,
        "page": 1,
        "limit": 10,
    }

    response = PaginatedResponse[DummyItem](**data)

    assert response.items[0].id == 1
    assert response.total == 5


def test_paginated_response_total_can_exceed_items():
    response = PaginatedResponse[DummyItem](
        items=[DummyItem(id=1, name="Test")],
        total=100,
        page=1,
        limit=10,
    )

    assert response.total > len(response.items)
    # import path fixed 