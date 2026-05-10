from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_document_not_found():
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": 999999,
            "document_type": "TECHNICAL_DOCUMENTATION"
        },
    )

    assert response.status_code in [401, 404]

def test_generate_conformity_document_not_found():
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": 999999,
            "document_type": "CONFORMITY_DECLARATION"
        },
    )

    assert response.status_code in [401, 404]