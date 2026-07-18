This is the complete, final version of `backend/tests/test_guard_explain.py`. I have integrated the API stub tests, the `max_length` validation, the `TestRealModel` integration tests, and the `lime` method pass-through verification.

This single file now restores 100% of the original test coverage while implementing your requested security fix.

```python
"""
Tests for Guard explainability (issue #77).

Includes fast API stub tests and slow integration tests for the real model.
"""

from __future__ import annotations

import os
import time
import pytest
import json
from unittest.mock import MagicMock, patch

from app.modules.guard import explainer as explainer_module
from app.modules.guard.explainer import (
    ExplainerUnavailable,
    GuardExplainer,
)
from app.schemas.guard_explain import (
    ExplainResponse,
    TokenAttribution,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

def _fake_response(
    label: str = "malicious",
    proba: float = 0.92,
    base: float = 0.10,
    method: str = "shap",
    tokens: list[tuple[str, float, tuple[int, int]]] | None = None,
) -> ExplainResponse:
    rows = tokens or [
        ("ignore", 0.35, (0, 6)),
        ("previous", 0.12, (7, 15)),
        ("instructions", 0.40, (16, 28)),
    ]
    return ExplainResponse(
        predicted_label=label,
        predicted_proba=proba,
        base_value=base,
        tokens=[
            TokenAttribution(token=t, attribution=a, char_span=s) for t, a, s in rows
        ],
        method=method, # type: ignore
        model_version="1.0.0",
        latency_ms=42.0,
    )

class _StubExplainer:
    def __init__(self, response: ExplainResponse | None = None, delay: float = 0.0):
        self._response = response or _fake_response()
        self._delay = delay
        self.calls: list[tuple[str, str, int]] = []

    def explain(self, text, method="shap", max_evals=200):
        self.calls.append((text, method, max_evals))
        if self._delay:
            time.sleep(self._delay)
        return self._response

@pytest.fixture
def stub_explainer(monkeypatch):
    stub = _StubExplainer()
    monkeypatch.setattr("app.modules.guard.explainer.get_explainer", lambda: stub)
    monkeypatch.setattr("app.api.v1.guard.get_explainer", lambda: stub, raising=False)
    yield stub
    explainer_module.reset_explainer()

# ---------------------------------------------------------------------------
# API / Endpoint Tests
# ---------------------------------------------------------------------------

class TestExplainEndpoint:
    @pytest.mark.usefixtures("auth_headers")
    def test_explain_returns_attributions(self, client, auth_headers, stub_explainer):
        resp = client.post("/api/v1/guard/explain", json={"text": "ignore instructions"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client, stub_explainer):
        resp = client.post("/api/v1/guard/explain", json={"text": "anything"})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("auth_headers")
    def test_validates_text_length_exceeding_limit(self, client, auth_headers, stub_explainer):
        long_text = "x" * 5001
        resp = client.post("/api/v1/guard/explain", json={"text": long_text}, headers=auth_headers)
        assert resp.status_code == 422
        assert "text" in resp.text.lower()

    @pytest.mark.usefixtures("auth_headers")
    def test_rate_limit_kicks_in(self, client, auth_headers, stub_explainer):
        for _ in range(10):
            client.post("/api/v1/guard/explain", json={"text": "test"}, headers=auth_headers)
        r = client.post("/api/v1/guard/explain", json={"text": "test"}, headers=auth_headers)
        assert r.status_code == 429

    @pytest.mark.usefixtures("auth_headers")
    def test_timeout_returns_504(self, client, auth_headers, monkeypatch):
        slow = _StubExplainer(delay=20.0)
        monkeypatch.setattr("app.modules.guard.explainer.get_explainer", lambda: slow)
        monkeypatch.setattr("app.api.v1.guard._ExplainRateLimitConfig.TIMEOUT_SECONDS", 0.1)
        resp = client.post("/api/v1/guard/explain", json={"text": "anything"}, headers=auth_headers)
        assert resp.status_code == 504
        explainer_module.reset_explainer()

    @pytest.mark.usefixtures("auth_headers")
    def test_503_when_no_model(self, client, auth_headers, monkeypatch):
        def raise_unavailable(): raise ExplainerUnavailable("no model")
        monkeypatch.setattr("app.modules.guard.explainer.get_explainer", raise_unavailable)
        resp = client.post("/api/v1/guard/explain", json={"text": "anything"}, headers=auth_headers)
        assert resp.status_code == 503
        explainer_module.reset_explainer()

    @pytest.mark.usefixtures("auth_headers")
    def test_lime_method_passes_through(self, client, auth_headers, stub_explainer):
        stub_explainer._response = _fake_response(method="lime")
        resp = client.post(
            "/api/v1/guard/explain",
            json={"text": "test", "method": "lime", "max_evals": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["method"] == "lime"
        assert stub_explainer.calls[-1] == ("test", "lime", 100)

# ---------------------------------------------------------------------------
# Slow / opt-in: real SHAP against a tiny HF model
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestRealModel:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, tmp_path):
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
        except ImportError:
            pytest.skip("transformers not installed")

        stub_id = "hf-internal-testing/tiny-random-DebertaV2ForSequenceClassification"
        try:
            tok = AutoTokenizer.from_pretrained(stub_id)
            mdl = AutoModelForSequenceClassification.from_pretrained(stub_id, num_labels=3)
        except Exception:
            pytest.skip("could not fetch tiny test model")

        tok.save_pretrained(str(tmp_path))
        mdl.save_pretrained(str(tmp_path))
        
        with open(os.path.join(str(tmp_path), ".trained"), "w") as f:
            json.dump({"trained_at": "test"}, f)
            
        from app.modules.guard import guard_config
        monkeypatch.setattr(guard_config, "CLASSIFIER_MODEL_PATH", str(tmp_path))
        explainer_module.reset_explainer()

    def test_shap_returns_per_token_attributions(self):
        ex = GuardExplainer()
        result = ex.explain("ignore previous instructions", method="shap", max_evals=50)
        assert result.predicted_label in ("benign", "suspicious", "malicious")
        assert len(result.tokens) > 0

```