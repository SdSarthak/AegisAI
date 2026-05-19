import pytest
from app.core.config import settings

SCIM_HEADERS = {
    "Authorization": f"Bearer {settings.SCIM_BEARER_TOKEN}",
    "Content-Type": "application/scim+json"
}

def test_unauthorized_scim_request(client):
    # Missing token
    response = client.post("/scim/v2/Users", json={})
    assert response.status_code == 401
    
    # Invalid token
    response = client.post("/scim/v2/Users", json={}, headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401

def test_scim_user_lifecycle(client):
    # 1. Create a user via SCIM POST
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "jane.doe@example.com",
        "name": {
            "formatted": "Jane Doe",
            "givenName": "Jane",
            "familyName": "Doe"
        },
        "emails": [
            {
                "value": "jane.doe@example.com",
                "type": "work",
                "primary": True
            }
        ],
        "active": True,
        "externalId": "ext-jane-doe-123"
    }
    
    response = client.post("/scim/v2/Users", json=payload, headers=SCIM_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["userName"] == "jane.doe@example.com"
    assert data["name"]["formatted"] == "Jane Doe"
    assert data["active"] is True
    assert data["externalId"] == "ext-jane-doe-123"
    user_id = data["id"]
    
    # 2. Get user by ID
    response = client.get(f"/scim/v2/Users/{user_id}", headers=SCIM_HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == user_id
    
    # 3. Filter user by userName
    response = client.get(f'/scim/v2/Users?filter=userName eq "jane.doe@example.com"', headers=SCIM_HEADERS)
    assert response.status_code == 200
    list_data = response.json()
    assert list_data["totalResults"] == 1
    assert list_data["Resources"][0]["id"] == user_id
    
    # 4. Update user (PUT)
    payload["name"]["formatted"] = "Jane Smith"
    response = client.put(f"/scim/v2/Users/{user_id}", json=payload, headers=SCIM_HEADERS)
    assert response.status_code == 200
    assert response.json()["name"]["formatted"] == "Jane Smith"
    
    # 5. Patch user (deactivate)
    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "active",
                "value": False
            }
        ]
    }
    response = client.patch(f"/scim/v2/Users/{user_id}", json=patch_payload, headers=SCIM_HEADERS)
    assert response.status_code == 200
    assert response.json()["active"] is False

    # 6. Delete user
    response = client.delete(f"/scim/v2/Users/{user_id}", headers=SCIM_HEADERS)
    assert response.status_code == 204
    
    # Verify user is gone
    response = client.get(f"/scim/v2/Users/{user_id}", headers=SCIM_HEADERS)
    assert response.status_code == 404

def test_scim_groups_mock(client):
    # Get Groups (should return empty list per mock setup)
    response = client.get("/scim/v2/Groups", headers=SCIM_HEADERS)
    assert response.status_code == 200
    assert response.json()["totalResults"] == 0
    
    # Post Group (mocked)
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": "Engineering Admins",
        "externalId": "ext-eng-admins"
    }
    response = client.post("/scim/v2/Groups", json=payload, headers=SCIM_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["displayName"] == "Engineering Admins"
    assert data["id"] == "mock-group-id"
