"""Integration test for full compliance workflow."""

import pytest
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.models.user import User
from app.core.security import create_access_token

@pytest.fixture
def test_user(client, db_session):
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$R9h31cIPz0yO8W4gw2love.a4UtcWLU7pHPti3/T.D18SMsKvRHO2",
        is_active=True,
        company_name="Test Company"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_compliance_workflow(client, auth_headers, db_session):
    # Step 1: create AI system
    response = client.post(
        "/api/v1/ai-systems/",
        json={
            "name": "Compliance Test System",
            "description": "Test",
            "version": "1.0",
            "use_case": "Testing",
            "sector": "Technology"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    system_id = response.json()["id"]
    
    #Step 2: run classification
    response = client.post(
        f"/api/v1/classification/classify/{system_id}",
        json={"use_case_category": "healthcare"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "risk_level" in response.json()

    # Step 3: generate doc
    response = client.post(
        f"/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "technical_documentation"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["content"] != "" 
    doc_id = response.json()["id"]

    # Step 4: fetch document
    response = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["content"] != ""

    # Step 5: Delete system
    response = client.delete(
        f"/api/v1/ai-systems/{system_id}",
        headers=auth_headers
    )
    assert response.status_code == 204
