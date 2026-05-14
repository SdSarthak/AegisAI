"""Integration test for full status lifecycle of an AI System."""

import pytest
from fastapi.testclient import TestClient

def test_full_status_lifecycle(client: TestClient):
    """
    Integration test covering the complete status lifecycle:
    1. Register user
    2. Login
    3. Create AI System
    4. Verify initial status (not_started)
    5-7. Update and verify status transitions
    8. Cross-user isolation
    """
    
    # 1. Register a new user
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "lifecycle@example.com",
            "password": "Password1!",
            "full_name": "Lifecycle Tester"
        }
    )
    assert register_resp.status_code == 201

    # 2. Log in via POST /auth/login to get a JWT
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "lifecycle@example.com",
            "password": "Password1!"
        }
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create an AI system via POST /ai-systems/
    create_resp = client.post(
        "/api/v1/ai-systems/",
        headers=headers,
        json={
            "name": "Integration Test System",
            "description": "Testing full lifecycle"
        }
    )
    assert create_resp.status_code == 201
    system_id = create_resp.json()["id"]

    # 4. Verify the initial compliance_status is not_started
    get_resp_1 = client.get(f"/api/v1/ai-systems/{system_id}", headers=headers)
    assert get_resp_1.status_code == 200
    assert get_resp_1.json()["compliance_status"] == "not_started"

    # 5. Calls PATCH /ai-systems/{id}/status with compliance_status: in_progress
    patch_resp_1 = client.patch(
        f"/api/v1/ai-systems/{system_id}/status",
        headers=headers,
        json={"compliance_status": "in_progress"}
    )
    assert patch_resp_1.status_code == 200

    # 6. Calls GET /ai-systems/{id} and asserts the status is now in_progress
    get_resp_2 = client.get(f"/api/v1/ai-systems/{system_id}", headers=headers)
    assert get_resp_2.status_code == 200
    assert get_resp_2.json()["compliance_status"] == "in_progress"

    # 7. Repeats step 5->6 for the full lifecycle: in_progress -> under_review -> compliant
    
    # -> under_review
    patch_resp_2 = client.patch(
        f"/api/v1/ai-systems/{system_id}/status",
        headers=headers,
        json={"compliance_status": "under_review"}
    )
    assert patch_resp_2.status_code == 200
    
    get_resp_3 = client.get(f"/api/v1/ai-systems/{system_id}", headers=headers)
    assert get_resp_3.status_code == 200
    assert get_resp_3.json()["compliance_status"] == "under_review"
    
    # -> compliant
    patch_resp_3 = client.patch(
        f"/api/v1/ai-systems/{system_id}/status",
        headers=headers,
        json={"compliance_status": "compliant"}
    )
    assert patch_resp_3.status_code == 200
    
    get_resp_4 = client.get(f"/api/v1/ai-systems/{system_id}", headers=headers)
    assert get_resp_4.status_code == 200
    assert get_resp_4.json()["compliance_status"] == "compliant"

    # 8. Verifies that a second user cannot PATCH the first user's system (expect 404)
    # Register second user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@example.com",
            "password": "Password1!",
            "full_name": "Hacker Tester"
        }
    )
    # Login second user
    hacker_login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "hacker@example.com",
            "password": "Password1!"
        }
    )
    hacker_token = hacker_login_resp.json()["access_token"]
    hacker_headers = {"Authorization": f"Bearer {hacker_token}"}
    
    # Try to patch first user's system
    patch_resp_hacker = client.patch(
        f"/api/v1/ai-systems/{system_id}/status",
        headers=hacker_headers,
        json={"compliance_status": "not_started"}
    )
    assert patch_resp_hacker.status_code == 404
