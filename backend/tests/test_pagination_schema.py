import pytest
from pydantic import ValidationError
from app.schemas.pagination import PaginatedResponse, CursorPaginatedResponse
from typing import Dict, Any

def test_paginated_response_valid():
    data = {
        "items": ["a", "b", "c"],
        "total": 3,
        "skip": 0,
        "limit": 10
    }
    response = PaginatedResponse[str](**data)
    assert response.items == ["a", "b", "c"]
    assert response.total == 3
    assert response.skip == 0
    assert response.limit == 10

def test_paginated_response_empty_items():
    data = {
        "items": [],
        "total": 0,
        "skip": 0,
        "limit": 10
    }
    response = PaginatedResponse[str](**data)
    assert response.items == []
    assert response.total == 0

def test_paginated_response_serialization():
    data = {
        "items": ["a", "b"],
        "total": 2,
        "skip": 5,
        "limit": 10
    }
    response = PaginatedResponse[str](**data)
    
    # Check dict serialization
    assert response.model_dump() == data
    
    # Check json serialization
    json_data = response.model_dump_json()
    assert "items" in json_data
    assert "skip" in json_data

def test_paginated_response_missing_fields():
    with pytest.raises(ValidationError):
        PaginatedResponse[str](items=["a"])  # Missing total, skip, limit

def test_cursor_paginated_response_valid():
    data = {
        "items": [{"id": 1}],
        "limit": 10,
        "next_cursor": "abc123"
    }
    response = CursorPaginatedResponse[Dict[str, Any]](**data)
    assert response.items == [{"id": 1}]
    assert response.limit == 10
    assert response.next_cursor == "abc123"

def test_cursor_paginated_response_empty_items():
    data = {
        "items": [],
        "limit": 5
    }
    # next_cursor is optional and should default to None
    response = CursorPaginatedResponse[str](**data)
    assert response.items == []
    assert response.limit == 5
    assert response.next_cursor is None

def test_cursor_paginated_response_serialization():
    data = {
        "items": ["a"],
        "limit": 5,
        "next_cursor": "xyz"
    }
    response = CursorPaginatedResponse[str](**data)
    
    assert response.model_dump() == data
    
    json_data = response.model_dump_json()
    assert "xyz" in json_data
