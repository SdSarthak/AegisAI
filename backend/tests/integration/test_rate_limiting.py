"""Integration tests for per-user rate limiting on guard scan endpoint."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from app.core.security import create_access_token
from app.models.user import User


def _guard_result():
    return {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {
                "confidence": 0.99,
                "reasoning": "Safe prompt",
            },
            "regex_analysis": {
                "matched_patterns": [],
            },
        },
    }


def _authenticate_test_user(db_session):
    user = User(
        email="rate-limit-user@example.com",
        hashed_password="$2b$12$R9h31cIPz0yO8W4gw2love.a4UtcWLU7pHPti3/T.D18SMsKvRHO2",
        is_active=True,
        company_name="AegisAI Tests",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_per_user_rate_limit_blocks_61st_guard_scan_request(client, db_session):
    """After 60 rapid requests, the 61st request should be rate limited."""
    auth_headers = _authenticate_test_user(db_session)

    fake_guard_module = ModuleType("app.modules.guard.llm_guard")
    fake_guard_class = MagicMock()
    fake_guard_class.return_value.guard.return_value = _guard_result()
    fake_guard_module.LLMGuard = fake_guard_class

    fake_intent_classifier_module = ModuleType("app.modules.guard.intent_classifier")
    fake_intent_classifier_module.IntentClassifier = MagicMock()

    fake_llm_client_module = ModuleType("app.modules.llm.llm_client")
    fake_llm_client_module.LLMClient = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "app.modules.guard.llm_guard": fake_guard_module,
            "app.modules.guard.intent_classifier": fake_intent_classifier_module,
            "app.modules.llm.llm_client": fake_llm_client_module,
        },
    ):
        status_codes = []
        payload = {"prompt": "Hello, this is a harmless test prompt."}

        for _ in range(60):
            response = client.post(
                "/api/v1/guard/scan", json=payload, headers=auth_headers
            )
            status_codes.append(response.status_code)

        blocked_response = client.post(
            "/api/v1/guard/scan", json=payload, headers=auth_headers
        )

    assert all(code != 429 for code in status_codes)
    assert blocked_response.status_code == 429
    assert blocked_response.headers.get("Retry-After") is not None

    body = blocked_response.json()
    detail = str(body.get("detail", "")).lower()
    assert detail
    assert (
        "rate" in detail
        or "limit" in detail
        or "too many" in detail
        or "retry" in detail
    )
