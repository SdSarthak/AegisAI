import pytest
from unittest.mock import AsyncMock, patch
from fastapi import BackgroundTasks

from app.api.v1.webhooks import (
    _build_signature,
    _post_webhook_sync,
    _validate_webhook_url,
    deliver_webhook,
)
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


def test_validate_webhook_url_allows_valid_https():
    _validate_webhook_url("https://example.com/webhook")


def test_validate_webhook_url_allows_valid_http():
    _validate_webhook_url("http://example.com/webhook")


def test_validate_webhook_url_rejects_private_ip():
    with pytest.raises(ValueError, match="Private IP addresses are not allowed"):
        _validate_webhook_url("http://192.168.1.1/webhook")


def test_validate_webhook_url_rejects_loopback():
    with pytest.raises(ValueError, match="Private IP addresses are not allowed"):
        _validate_webhook_url("http://127.0.0.1/webhook")


def test_validate_webhook_url_rejects_link_local():
    with pytest.raises(ValueError, match="Private IP addresses are not allowed"):
        _validate_webhook_url("http://169.254.169.254/latest/meta-data/")


def test_validate_webhook_url_rejects_localhost():
    with pytest.raises(ValueError, match="not allowed"):
        _validate_webhook_url("http://localhost:8080/webhook")


def test_validate_webhook_url_rejects_internal_domain():
    with pytest.raises(ValueError, match="Internal domain names are not allowed"):
        _validate_webhook_url("http://service.internal/webhook")


def test_validate_webhook_url_rejects_local_domain():
    with pytest.raises(ValueError, match="Internal domain names are not allowed"):
        _validate_webhook_url("http://myserver.local/webhook")


def test_validate_webhook_url_rejects_ftp_scheme():
    with pytest.raises(ValueError, match="Only http and https URLs are allowed"):
        _validate_webhook_url("ftp://example.com/webhook")


def test_validate_webhook_url_rejects_file_scheme():
    with pytest.raises(ValueError, match="Only http and https URLs are allowed"):
        _validate_webhook_url("file:///etc/passwd")


def test_post_webhook_sync_calls_asyncio_run():
    """Verify _post_webhook_sync properly wraps the async _post_webhook function.

    BackgroundTasks.add_task() does not await async callables. The sync wrapper
    uses asyncio.run() to ensure the HTTP request is actually sent.
    Since asyncio.run() runs the coroutine synchronously, AsyncMock.assert_awaited
    does not work. Use a real coroutine function and verify it was called.
    """
    from unittest.mock import MagicMock
    call_tracker = MagicMock()

    async def fake_post(url, event, payload, secret):
        call_tracker(url=url, event=event, payload=payload, secret=secret)
        return None

    with patch("app.api.v1.webhooks._post_webhook", fake_post):
        _post_webhook_sync(
            url="https://example.com/webhook",
            event="guard_block",
            payload={"decision": "block"},
            secret=None,
        )

    call_tracker.assert_called_once_with(
        url="https://example.com/webhook",
        event="guard_block",
        payload={"decision": "block"},
        secret=None,
    )


def test_deliver_webhook_uses_sync_wrapper():
    """Verify deliver_webhook schedules the sync wrapper, not the raw async function."""
    webhook = WebhookConfig(
        user_id=1,
        url="https://example.com/webhook",
        secret=None,
        is_active=True,
        events=["guard_block"],
    )

    background_tasks = BackgroundTasks()

    # Verify that deliver_webhook schedules _post_webhook_sync, NOT the raw async
    # _post_webhook. BackgroundTasks.add_task() silently drops bare async callables.
    deliver_webhook(
        db=DummyDB([webhook]),
        user_id=1,
        event="guard_block",
        payload={"decision": "block"},
        background_tasks=background_tasks,
    )

    assert len(background_tasks.tasks) == 1
    # The scheduled function must be the sync wrapper, not the raw async.
    # If it were _post_webhook (raw async), BackgroundTasks would silently drop it.
    task_func = background_tasks.tasks[0].func
    # Check it is NOT the raw async function by verifying the function name.
    # _post_webhook is async (name starts with _), _post_webhook_sync is the wrapper.
    assert "_post_webhook_sync" in task_func.__name__ or task_func is _post_webhook_sync
