import asyncio
import hmac
import hashlib
import json

from app.models.webhook import WebhookConfig


def test_webhook_signature_and_delivery(db_session, monkeypatch):
    # Create a test webhook config that subscribes to 'guard_block'
    wh = WebhookConfig(user_id=1, url="http://example.invalid/webhook", secret="topsecret", is_active=True, events=["guard_block"]) 
    db_session.add(wh)
    db_session.commit()

    recorded = {}

    async def fake_post(self, url, content=None, headers=None, timeout=None):
        recorded['url'] = url
        recorded['content'] = content
        recorded['headers'] = headers
        class Resp:
            status_code = 200
        return Resp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    # Use FastAPI BackgroundTasks and make add_task run immediately in tests
    from fastapi import BackgroundTasks
    bt = BackgroundTasks()

    def immediate_add_task(func, *args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(func(*args, **kwargs))

    monkeypatch.setattr(bt, "add_task", immediate_add_task)

    from app.api.v1.webhooks import deliver_webhook

    payload = {"decision": "block"}

    deliver_webhook(db=db_session, user_id=1, event="guard_block", payload=payload, background_tasks=bt)

    assert recorded['url'] == "http://example.invalid/webhook"
    sent = json.loads(recorded['content'].decode('utf-8'))
    assert sent['event'] == 'guard_block'

    expected_sig = hmac.new(b"topsecret", recorded['content'], hashlib.sha256).hexdigest()
    assert recorded['headers']["X-AegisAI-Signature"] == expected_sig
