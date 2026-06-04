"""Unit tests for the EU AI Act risk classification endpoint.

Covers ``POST /api/v1/classification/classify`` across the risk levels the
engine can produce (MINIMAL, LIMITED, HIGH) plus boundary / edge cases where
several risk factors interact.

These tests exercise the endpoint through ``TestClient`` with
``get_current_user`` overridden, following the dependency-override pattern in
``test_auth_me.py``. The ``/classify`` route does not touch the database, so no
DB override is required.

Note on UNACCEPTABLE risk: the EU AI Act Article 5 (prohibited practices) path
is not yet implemented in ``classify_risk`` — it exists only as a comment. The
``RiskLevel.UNACCEPTABLE`` enum value is therefore never returned today. This is
documented and pinned by ``test_unacceptable_risk_not_yet_produced`` so the gap
is explicit rather than silently assumed to work.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier

CLASSIFY_URL = "/api/v1/classification/classify"


@pytest.fixture
def client():
    """TestClient with an authenticated dummy user; /classify needs no DB."""
    user = User(
        id=1,
        email="user@example.com",
        hashed_password="hashed",
        full_name="Test User",
        company_name="Test Co",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


def classify(client, **fields):
    """POST a classification request, returning the parsed JSON body."""
    payload = {"use_case_category": "general", **fields}
    response = client.post(CLASSIFY_URL, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# MINIMAL risk
# ---------------------------------------------------------------------------


class TestMinimalRisk:
    def test_no_risk_factors_is_minimal(self, client):
        # Defaults set interacts_with_humans / makes_automated_decisions True,
        # so a genuinely minimal system must opt out of the transparency flags.
        result = classify(
            client,
            use_case_category="internal_analytics",
            interacts_with_humans=False,
            makes_automated_decisions=False,
        )
        assert result["risk_level"] == "minimal"
        assert result["confidence"] == 0.9

    def test_minimal_has_no_mandatory_requirements_message(self, client):
        result = classify(
            client,
            interacts_with_humans=False,
            makes_automated_decisions=False,
        )
        assert any("voluntary" in r.lower() for r in result["requirements"])

    def test_biometric_data_alone_does_not_raise_risk(self, client):
        # uses_biometric_data is collected but not used by classify_risk today;
        # on its own it leaves the system at MINIMAL. Pins current behaviour.
        result = classify(
            client,
            uses_biometric_data=True,
            interacts_with_humans=False,
            makes_automated_decisions=False,
        )
        assert result["risk_level"] == "minimal"


# ---------------------------------------------------------------------------
# LIMITED risk (Article 52 transparency obligations)
# ---------------------------------------------------------------------------


class TestLimitedRisk:
    def test_chatbot_interaction_is_limited(self, client):
        result = classify(client, interacts_with_humans=True)
        assert result["risk_level"] == "limited"
        assert any("Article 52" in r for r in result["requirements"])

    def test_emotion_recognition_is_limited(self, client):
        result = classify(
            client,
            interacts_with_humans=False,
            emotion_recognition=True,
        )
        assert result["risk_level"] == "limited"

    def test_synthetic_content_is_limited(self, client):
        result = classify(
            client,
            interacts_with_humans=False,
            generates_synthetic_content=True,
        )
        assert result["risk_level"] == "limited"
        assert any("label" in r.lower() for r in result["requirements"])


# ---------------------------------------------------------------------------
# HIGH risk (Article 6 + Annex III)
# ---------------------------------------------------------------------------


class TestHighRisk:
    @pytest.mark.parametrize(
        "factor",
        [
            "hr_recruitment_screening",
            "hr_promotion_termination",
            "credit_worthiness",
            "insurance_risk_assessment",
            "is_safety_component",
            "affects_fundamental_rights",
            "law_enforcement",
            "border_control",
            "justice_system",
        ],
    )
    def test_single_high_risk_factor_triggers_high(self, client, factor):
        result = classify(client, **{factor: True})
        assert result["risk_level"] == "high"

    def test_high_risk_includes_compliance_requirements(self, client):
        result = classify(client, hr_recruitment_screening=True)
        assert result["requirements"], "HIGH risk must list mandatory requirements"
        assert any("Article 9" in r for r in result["requirements"])

    def test_high_risk_has_next_steps(self, client):
        result = classify(client, credit_worthiness=True)
        assert any(
            "risk assessment" in s.lower() for s in result["next_steps"]
        )


# ---------------------------------------------------------------------------
# Boundary / edge cases
# ---------------------------------------------------------------------------


class TestBoundaryCases:
    def test_high_takes_precedence_over_limited(self, client):
        # A recruitment chatbot trips both Annex III (HIGH) and Article 52
        # (LIMITED); HIGH must win.
        result = classify(
            client,
            interacts_with_humans=True,
            hr_recruitment_screening=True,
        )
        assert result["risk_level"] == "high"

    def test_multiple_high_factors_accumulate_reasons(self, client):
        single = classify(client, hr_recruitment_screening=True)
        multi = classify(
            client,
            hr_recruitment_screening=True,
            credit_worthiness=True,
            law_enforcement=True,
        )
        assert len(multi["reasons"]) > len(single["reasons"])

    def test_missing_use_case_category_is_rejected(self, client):
        # use_case_category is the only required field.
        response = client.post(CLASSIFY_URL, json={"interacts_with_humans": False})
        assert response.status_code == 422

    def test_unauthenticated_request_is_rejected(self):
        # No get_current_user override -> auth dependency must reject.
        app.dependency_overrides.clear()
        response = TestClient(app).post(
            CLASSIFY_URL, json={"use_case_category": "general"}
        )
        assert response.status_code in (401, 403)

    def test_unacceptable_risk_not_yet_produced(self, client):
        # Article 5 prohibited-practice detection is unimplemented, so even
        # inputs that flip every available flag never yield UNACCEPTABLE.
        # This test documents the gap; update it when Article 5 lands.
        result = classify(
            client,
            use_case_category="social_scoring",
            is_safety_component=True,
            affects_fundamental_rights=True,
            uses_biometric_data=True,
            makes_automated_decisions=True,
            hr_recruitment_screening=True,
            law_enforcement=True,
            biometric_categorization=True,
        )
        assert result["risk_level"] != "unacceptable"
        assert result["risk_level"] == "high"
