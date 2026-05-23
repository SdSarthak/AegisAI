import asyncio
import hashlib
import hmac
import json

import httpx
import pytest
import respx

from app.core.security import create_access_token
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.api.v1.webhooks import deliver_webhook


@pytest.fixture
def test_user(db_session):
    user = User(email="webhook-user@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    user = User(email="webhook-other@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_create_webhook(client, auth_headers, db_session):
    response = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["guard_block"],
            "secret": "topsecret",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["url"] == "https://example.com/webhook"
    assert data["events"] == ["guard_block"]

    row = db_session.query(WebhookConfig).filter(WebhookConfig.id == data["id"]).first()
    assert row is not None


def test_list_webhooks_empty(client, auth_headers):
    response = client.get("/api/v1/webhooks", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_webhooks_scoped(client, auth_headers, db_session, test_user, other_user):
    own = WebhookConfig(
        user_id=test_user.id,
        url="https://example.com/own",
        events=["guard_block"],
        secret="own",
        is_active=True,
    )
    other = WebhookConfig(
        user_id=other_user.id,
        url="https://example.com/other",
        events=["guard_block"],
        secret="other",
        is_active=True,
    )
    db_session.add_all([own, other])
    db_session.commit()

    response = client.get("/api/v1/webhooks", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["url"] == "https://example.com/own"


def test_delete_webhook_own(client, auth_headers, db_session, test_user):
    config = WebhookConfig(
        user_id=test_user.id,
        url="https://example.com/delete",
        events=["guard_block"],
        secret="delete",
        is_active=True,
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)

    response = client.delete(f"/api/v1/webhooks/{config.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"detail": "deleted"}


def test_delete_webhook_other_user(client, auth_headers, db_session, other_user):
    config = WebhookConfig(
        user_id=other_user.id,
        url="https://example.com/other-delete",
        events=["guard_block"],
        secret="other",
        is_active=True,
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)

    response = client.delete(f"/api/v1/webhooks/{config.id}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_deliver_webhook_sends_correct_headers(db_session, test_user):
    payload = {"message": "blocked", "score": 0.99}
    event = "guard_block"
    secret = "signing-secret"
    body = json.dumps(payload, separators=(",", ":")).encode()
    config = WebhookConfig(
        user_id=test_user.id,
        url="https://example.com/deliver",
        events=[event],
        secret=secret,
        is_active=True,
    )
    db_session.add(config)
    db_session.commit()

    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://example.com/deliver").mock(
            return_value=httpx.Response(200)
        )
        asyncio.run(deliver_webhook(db_session, test_user.id, event, payload))

    request = route.calls.last.request
    signature = request.headers["X-AegisAI-Signature"]
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert request.headers["X-AegisAI-Event"] == event
    assert signature.startswith("sha256=")
    assert signature == f"sha256={expected}"


def test_deliver_webhook_ignores_failed_delivery(db_session, test_user):
    event = "guard_block"
    config = WebhookConfig(
        user_id=test_user.id,
        url="https://example.com/fail",
        events=[event],
        secret="secret",
        is_active=True,
    )
    db_session.add(config)
    db_session.commit()

    with respx.mock(assert_all_called=True) as router:
        router.post("https://example.com/fail").mock(
            side_effect=httpx.ConnectError("connection failed")
        )
        asyncio.run(deliver_webhook(db_session, test_user.id, event, {"ok": True}))
