from fastapi import BackgroundTasks

from app.api.v1.webhooks import _build_signature, deliver_webhook
from app.models.webhook import WebhookConfig


class DummyQuery:
    def __init__(self, webhooks):
        self.webhooks = webhooks

    def filter(self, *args):
        return self

    def all(self):
        return self.webhooks


class DummyDB:
    def __init__(self, webhooks):
        self.webhooks = webhooks

    def query(self, model):
        return DummyQuery(self.webhooks)


def test_build_signature_generates_hmac_sha256():
    signature = _build_signature("secret", b'{"decision":"block"}')

    assert isinstance(signature, str)
    assert len(signature) == 64


def test_deliver_webhook_schedules_matching_active_webhook():
    webhook = WebhookConfig(
        user_id=1,
        url="https://example.com/webhook",
        secret="secret",
        is_active=True,
        events=["guard_block"],
    )

    background_tasks = BackgroundTasks()

    deliver_webhook(
        db=DummyDB([webhook]),
        user_id=1,
        event="guard_block",
        payload={"decision": "block"},
        background_tasks=background_tasks,
    )

    assert len(background_tasks.tasks) == 1


def test_deliver_webhook_ignores_unsubscribed_event():
    webhook = WebhookConfig(
        user_id=1,
        url="https://example.com/webhook",
        secret="secret",
        is_active=True,
        events=["compliance_drift"],
    )

    background_tasks = BackgroundTasks()

    deliver_webhook(
        db=DummyDB([webhook]),
        user_id=1,
        event="guard_block",
        payload={"decision": "block"},
        background_tasks=background_tasks,
    )

    assert len(background_tasks.tasks) == 0