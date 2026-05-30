"""
Integration tests for the Organisations API (issue #85).

Tests cover:
    - Creating an organisation
    - Org slug validation and auto-generation
    - Getting org details (member vs. non-member access)
    - Updating org name (admin only)
    - Listing members
    - Inviting a member by email
    - Inviting a non-existent user
    - Member cannot invite
    - Removing a member
    - AI system org-scoping (members see each other's systems)
    - Cannot remove org owner
    - Cannot create two orgs
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str, password: str = "Passw0rd!") -> str:
    """Register a user and return a bearer token."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_token(client):
    return _register_and_login(client, "org_admin@example.com")


@pytest.fixture
def member_token(client):
    return _register_and_login(client, "org_member@example.com")


@pytest.fixture
def outsider_token(client):
    return _register_and_login(client, "outsider@example.com")


@pytest.fixture
def org_id(client, admin_token):
    """Create an org as admin and return the org id."""
    resp = client.post(
        "/api/v1/orgs/",
        json={"name": "Acme Corp"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Create Org
# ---------------------------------------------------------------------------

class TestCreateOrg:
    def test_create_org_success(self, client, admin_token):
        resp = client.post(
            "/api/v1/orgs/",
            json={"name": "Test Org"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Org"
        assert data["slug"] == "test-org"
        assert data["member_count"] == 1  # Creator is the first member

    def test_create_org_custom_slug(self, client, admin_token):
        resp = client.post(
            "/api/v1/orgs/",
            json={"name": "My Org", "slug": "my-custom-slug"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["slug"] == "my-custom-slug"

    def test_create_org_invalid_slug(self, client, admin_token):
        resp = client.post(
            "/api/v1/orgs/",
            json={"name": "Bad Slug", "slug": "Bad Slug With Spaces"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 422  # Validation error

    def test_cannot_create_second_org(self, client, admin_token, org_id):
        """A user who already belongs to an org cannot create another."""
        resp = client.post(
            "/api/v1/orgs/",
            json={"name": "Another Org"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400

    def test_unauthenticated_cannot_create_org(self, client):
        resp = client.post("/api/v1/orgs/", json={"name": "Ghost Org"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get Org
# ---------------------------------------------------------------------------

class TestGetOrg:
    def test_get_org_as_member(self, client, admin_token, org_id):
        resp = client.get(f"/api/v1/orgs/{org_id}", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == org_id
        assert "slug" in data
        assert "member_count" in data

    def test_get_org_as_outsider_is_forbidden(self, client, outsider_token, org_id):
        resp = client.get(f"/api/v1/orgs/{org_id}", headers=_auth(outsider_token))
        assert resp.status_code == 403

    def test_get_nonexistent_org(self, client, admin_token):
        resp = client.get("/api/v1/orgs/99999", headers=_auth(admin_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Org
# ---------------------------------------------------------------------------

class TestUpdateOrg:
    def test_admin_can_update_name(self, client, admin_token, org_id):
        resp = client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"name": "Acme Corp Renamed"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme Corp Renamed"

    def test_member_cannot_update_org(self, client, admin_token, member_token, org_id):
        # Invite the member first
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        resp = client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"name": "Hacked Name"},
            headers=_auth(member_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Invite Member
# ---------------------------------------------------------------------------

class TestInviteMember:
    def test_admin_can_invite_user(self, client, admin_token, member_token, org_id):
        resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "org_member@example.com"
        assert data["role"] == "member"

    def test_invite_nonexistent_user_returns_404(self, client, admin_token, org_id):
        resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "ghost@example.com"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404

    def test_duplicate_invite_returns_409(self, client, admin_token, member_token, org_id):
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 409

    def test_member_cannot_invite(self, client, admin_token, member_token, outsider_token, org_id):
        # Invite member first
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        # Member tries to invite outsider
        resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "outsider@example.com"},
            headers=_auth(member_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# List Members
# ---------------------------------------------------------------------------

class TestListMembers:
    def test_admin_can_list_members(self, client, admin_token, member_token, org_id):
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        resp = client.get(f"/api/v1/orgs/{org_id}/members", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        emails = [m["email"] for m in data["members"]]
        assert "org_admin@example.com" in emails
        assert "org_member@example.com" in emails

    def test_outsider_cannot_list_members(self, client, outsider_token, org_id):
        resp = client.get(f"/api/v1/orgs/{org_id}/members", headers=_auth(outsider_token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Remove Member
# ---------------------------------------------------------------------------

class TestRemoveMember:
    def _get_user_id_from_token(self, client: TestClient, token: str) -> int:
        resp = client.get("/api/v1/auth/me", headers=_auth(token))
        return resp.json()["id"]

    def test_admin_can_remove_member(self, client, admin_token, member_token, org_id):
        # Invite member
        invite_resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        member_user_id = invite_resp.json()["user_id"]

        # Remove them
        resp = client.delete(
            f"/api/v1/orgs/{org_id}/members/{member_user_id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 204

        # Member count should be back to 1
        list_resp = client.get(f"/api/v1/orgs/{org_id}/members", headers=_auth(admin_token))
        assert list_resp.json()["total"] == 1

    def test_cannot_remove_org_owner(self, client, admin_token, org_id):
        owner_id = self._get_user_id_from_token(client, admin_token)
        resp = client.delete(
            f"/api/v1/orgs/{org_id}/members/{owner_id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 400

    def test_member_cannot_remove_others(self, client, admin_token, member_token, outsider_token, org_id):
        # Invite two users
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )
        outsider_invite_resp = client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "outsider@example.com"},
            headers=_auth(admin_token),
        )
        outsider_user_id = outsider_invite_resp.json()["user_id"]

        # Regular member tries to remove outsider
        resp = client.delete(
            f"/api/v1/orgs/{org_id}/members/{outsider_user_id}",
            headers=_auth(member_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# AI System Org Scoping
# ---------------------------------------------------------------------------

class TestAISystemOrgScoping:
    def test_org_member_sees_all_org_ai_systems(self, client, admin_token, member_token, org_id):
        """A member should see AI systems created by any org member."""
        # Invite member
        client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "org_member@example.com"},
            headers=_auth(admin_token),
        )

        # Admin creates an AI system
        create_resp = client.post(
            "/api/v1/ai-systems/",
            json={"name": "Org Shared System", "description": "Shared across org"},
            headers=_auth(admin_token),
        )
        assert create_resp.status_code == 201

        # Member lists AI systems — should see admin's system
        list_resp = client.get("/api/v1/ai-systems/", headers=_auth(member_token))
        assert list_resp.status_code == 200
        names = [s["name"] for s in list_resp.json()["items"]]
        assert "Org Shared System" in names

    def test_outsider_cannot_see_org_ai_systems(self, client, admin_token, outsider_token, org_id):
        """A user outside the org should NOT see org-scoped AI systems."""
        client.post(
            "/api/v1/ai-systems/",
            json={"name": "Private Org System"},
            headers=_auth(admin_token),
        )

        list_resp = client.get("/api/v1/ai-systems/", headers=_auth(outsider_token))
        assert list_resp.status_code == 200
        names = [s["name"] for s in list_resp.json()["items"]]
        assert "Private Org System" not in names
