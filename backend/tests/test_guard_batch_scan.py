"""Tests for the Guard batch scan endpoint validation behavior."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.rate_limit import guard_scan_rate_limiter


def _guard_result():
    return {
        "decision": "allow",
        "metadata": {
            "regex_analysis": {
                "flag": False,
                "risk_score": 0.0,
                "matched_patterns": [],
            },
            "intent_analysis": {
                "intent": "benign",
                "confidence": 0.99,
            },
            "decision_reasoning": {
                "confidence": 0.99,
                "reasoning": "Safe prompt",
            },
        },
    }


def test_batch_scan_accepts_standard_valid_batch_request(client, auth_headers):
    payload = {
        "prompts": [
            "Summarize the EU AI Act risk categories.",
            "What is a safe model monitoring checklist?",
        ]
    }

    with patch("app.modules.guard.llm_guard.LLMGuard") as mock_guard_class:
        mock_guard = mock_guard_class.return_value
        mock_guard.guard.return_value = _guard_result()

        response = client.post(
            "/api/v1/guard/scan/batch",
            json=payload,
            headers=auth_headers,
        )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["processed"] == 2
    assert len(data["results"]) == 2
    assert {result["decision"] for result in data["results"]} == {"allow"}
    assert mock_guard.guard.call_count == 2


def test_batch_scan_rejects_empty_batch_payload(client, auth_headers):
    response = client.post(
        "/api/v1/guard/scan/batch",
        json={"prompts": []},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "At least one prompt is required per batch request."
    }


def test_batch_scan_rejects_payload_exceeding_validate_prompts_limit(
    client,
    auth_headers,
):
    payload = {"prompts": [f"Prompt {index}" for index in range(51)]}

    response = client.post(
        "/api/v1/guard/scan/batch",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Maximum 50 prompts allowed per batch request."
    }


def test_batch_scan_rejects_prompt_over_configured_length(client, auth_headers):
    oversized_prompt = "x" * (settings.GUARD_MAX_PROMPT_LENGTH + 1)

    with patch("app.modules.guard.llm_guard.LLMGuard") as mock_guard_class:
        response = client.post(
            "/api/v1/guard/scan/batch",
            json={"prompts": ["normal prompt", oversized_prompt]},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Prompt at index 1 must be between 1 and "
            f"{settings.GUARD_MAX_PROMPT_LENGTH} characters."
        )
    }
    mock_guard_class.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"prompts": "this should be a list"},
        {"prompts": [{"text": "objects are not valid prompt strings"}]},
    ],
)
def test_batch_scan_rejects_malformed_payload_without_server_error(
    client,
    auth_headers,
    payload,
):
    response = client.post(
        "/api/v1/guard/scan/batch",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "detail" in response.json()
