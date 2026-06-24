"""
Pytest tests for POST /api/v1/classification/classify endpoint.

Covers:
- MINIMAL risk AI systems
- HIGH risk AI systems
- UNACCEPTABLE risk AI systems  (note: the engine maps these to HIGH;
  the EU AI Act prohibited-practice check is not yet wired in the
  classify_risk() function, so we test the observable behaviour)
- Boundary / edge cases

Follows the pattern established in backend/tests/test_guard.py.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from .csrf_helpers import _CSRFClientWrapper
 
 
# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------
 
# All-false baseline → MINIMAL risk
MINIMAL_PAYLOAD = {
    "use_case_category": "entertainment",
    "is_safety_component": False,
    "affects_fundamental_rights": False,
    "uses_biometric_data": False,
    "makes_automated_decisions": False,
    "hr_recruitment_screening": False,
    "hr_promotion_termination": False,
    "credit_worthiness": False,
    "insurance_risk_assessment": False,
    "law_enforcement": False,
    "border_control": False,
    "justice_system": False,
    "interacts_with_humans": False,
    "generates_synthetic_content": False,
    "emotion_recognition": False,
    "biometric_categorization": False,
}
 
# HR flag → HIGH risk
HIGH_PAYLOAD = {
    **MINIMAL_PAYLOAD,
    "use_case_category": "hr_recruitment",
    "hr_recruitment_screening": True,
}
 
# Law-enforcement flag → HIGH risk (closest observable proxy for
# what would be UNACCEPTABLE in a fuller implementation)
UNACCEPTABLE_PROXY_PAYLOAD = {
    **MINIMAL_PAYLOAD,
    "use_case_category": "law_enforcement",
    "law_enforcement": True,
    "uses_biometric_data": True,
}
 
# Chatbot → LIMITED risk
LIMITED_PAYLOAD = {
    **MINIMAL_PAYLOAD,
    "use_case_category": "customer_service",
    "interacts_with_humans": True,
}
 
 
# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------
def _make_client():
    """
    Return a FastAPI TestClient with authentication bypassed.
    Uses dependency_overrides to skip JWT validation entirely.

    Pre-fetches a CSRF token so that POST/PUT/PATCH/DELETE requests
    succeed when CSRF protection is enabled on the app.
    """
    from app.main import app
    from app.core.security import get_current_user

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"

    # Override BEFORE creating the client — overrides persist on the app object
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)
    # Wrap in _CSRFClientWrapper so POST requests auto-inject CSRF tokens
    return _CSRFClientWrapper(client)
 
 
# ---------------------------------------------------------------------------
# MINIMAL risk tests
# ---------------------------------------------------------------------------
 
class TestMinimalRiskClassification:
    """POST /api/v1/classification/classify — MINIMAL risk systems."""
 
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()
 
    def test_spam_filter_is_minimal_risk(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json={**MINIMAL_PAYLOAD, "use_case_category": "spam_filter"},
        )
 
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "minimal"
 
    def test_minimal_risk_response_has_required_fields(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        data = response.json()
        assert "risk_level" in data
        assert "confidence" in data
        assert "reasons" in data
        assert "requirements" in data
        assert "next_steps" in data
 
    def test_minimal_risk_confidence_is_bounded(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0
 
    @pytest.mark.parametrize(
        "use_case_category",
        [
            "music_recommendation",
            "recipe_suggestion",
            "spam_filter",
            "autocomplete",
        ],
    )
    def test_minimal_risk_matrix(self, use_case_category):
        payload = {**MINIMAL_PAYLOAD, "use_case_category": use_case_category}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "minimal"
 
 
# ---------------------------------------------------------------------------
# HIGH risk tests
# ---------------------------------------------------------------------------
 
class TestHighRiskClassification:
    """POST /api/v1/classification/classify — HIGH risk systems."""
 
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()
 
    def test_hr_recruitment_is_high_risk(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=HIGH_PAYLOAD,
        )
 
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "high"
 
    def test_credit_scoring_is_high_risk(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "credit_scoring",
            "credit_worthiness": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
    def test_safety_component_is_high_risk(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "industrial_safety",
            "is_safety_component": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
    def test_high_risk_returns_requirements(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=HIGH_PAYLOAD,
        )
 
        data = response.json()
        assert isinstance(data["requirements"], list)
        assert len(data["requirements"]) > 0
 
    def test_high_risk_returns_next_steps(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=HIGH_PAYLOAD,
        )
 
        data = response.json()
        assert isinstance(data["next_steps"], list)
        assert len(data["next_steps"]) > 0
 
    @pytest.mark.parametrize(
        "flag,use_case",
        [
            ("hr_recruitment_screening", "hr_recruitment"),
            ("hr_promotion_termination", "hr_management"),
            ("credit_worthiness", "credit_scoring"),
            ("insurance_risk_assessment", "insurance"),
            ("law_enforcement", "law_enforcement"),
            ("border_control", "border_control"),
            ("justice_system", "justice"),
            ("is_safety_component", "industrial_safety"),
            ("affects_fundamental_rights", "public_service"),
        ],
    )
    def test_high_risk_matrix(self, flag, use_case):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": use_case,
            flag: True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
 
# ---------------------------------------------------------------------------
# UNACCEPTABLE / prohibited-use proxy tests
# ---------------------------------------------------------------------------
 
class TestUnacceptableRiskClassification:
    """
    POST /api/v1/classification/classify — systems that would be
    UNACCEPTABLE under Article 5 of the EU AI Act.
 
    The current classify_risk() implementation maps these to HIGH risk
    (the prohibited-practice gate is not yet wired).  These tests verify
    that such systems are at minimum flagged as HIGH risk and never
    returned as MINIMAL or LIMITED.
    """
 
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()
 
    def test_biometric_law_enforcement_is_not_minimal(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=UNACCEPTABLE_PROXY_PAYLOAD,
        )
 
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] != "minimal"
        assert data["risk_level"] != "limited"
 
    def test_biometric_law_enforcement_is_high_risk(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=UNACCEPTABLE_PROXY_PAYLOAD,
        )
 
        assert response.json()["risk_level"] == "high"
 
    def test_border_control_biometrics_is_high_risk(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "border_control",
            "border_control": True,
            "uses_biometric_data": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
    @pytest.mark.parametrize(
        "payload_overrides,use_case",
        [
            (
                {"law_enforcement": True, "uses_biometric_data": True},
                "real_time_biometric_surveillance",
            ),
            (
                {"border_control": True, "uses_biometric_data": True},
                "border_biometric_screening",
            ),
            (
                {"justice_system": True, "makes_automated_decisions": True},
                "automated_sentencing",
            ),
        ],
    )
    def test_unacceptable_proxy_matrix(self, payload_overrides, use_case):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": use_case,
            **payload_overrides,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        data = response.json()
        # Must be at least HIGH — never slips through as low risk
        assert data["risk_level"] == "high"
 
 
# ---------------------------------------------------------------------------
# LIMITED risk tests
# ---------------------------------------------------------------------------
 
class TestLimitedRiskClassification:
    """POST /api/v1/classification/classify — LIMITED risk systems."""
 
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()
 
    def test_chatbot_is_limited_risk(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=LIMITED_PAYLOAD,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "limited"
 
    def test_emotion_recognition_is_limited_risk(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "emotion_recognition",
            "emotion_recognition": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "limited"
 
    def test_synthetic_content_is_limited_risk(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "deepfake_detection",
            "generates_synthetic_content": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "limited"
 
 
# ---------------------------------------------------------------------------
# Boundary / edge case tests
# ---------------------------------------------------------------------------
 
class TestClassificationEdgeCases:
    """Boundary and edge cases."""
 
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()
 
    def test_missing_use_case_category_returns_422(self):
        payload = {k: v for k, v in MINIMAL_PAYLOAD.items() if k != "use_case_category"}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 422
 
    def test_empty_body_returns_422(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json={},
        )
 
        assert response.status_code == 422
 
    def test_non_json_body_returns_error(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            data="not-json",
            headers={"Content-Type": "text/plain"},
        )
 
        assert response.status_code in (400, 415, 422)
 
    def test_response_content_type_is_json(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert response.headers["content-type"].startswith("application/json")
 
    def test_risk_level_is_one_of_valid_values(self):
        valid_levels = {"minimal", "limited", "high", "unacceptable"}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert response.json()["risk_level"] in valid_levels
 
    def test_confidence_is_between_0_and_1(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        confidence = response.json()["confidence"]
        assert 0.0 <= confidence <= 1.0
 
    def test_reasons_is_a_list(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert isinstance(response.json()["reasons"], list)
 
    def test_requirements_is_a_list(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert isinstance(response.json()["requirements"], list)
 
    def test_next_steps_is_a_list(self):
        response = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert isinstance(response.json()["next_steps"], list)
 
    def test_get_method_not_allowed(self):
        response = self.client.get("/api/v1/classification/classify")
 
        assert response.status_code == 405
 
    def test_put_method_not_allowed(self):
        response = self.client.put(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert response.status_code == 405
 
    def test_identical_requests_return_same_risk_level(self):
        r1 = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
        r2 = self.client.post(
            "/api/v1/classification/classify",
            json=MINIMAL_PAYLOAD,
        )
 
        assert r1.json()["risk_level"] == r2.json()["risk_level"]
 
    def test_invalid_boolean_field_returns_422(self):
        payload = {**MINIMAL_PAYLOAD, "is_safety_component": "not-a-bool"}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 422
 
    def test_extra_unknown_fields_are_ignored(self):
        payload = {**MINIMAL_PAYLOAD, "unknown_future_field": "ignored"}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        # Should not crash — extra fields are silently ignored by Pydantic
        assert response.status_code in (200, 422)
 
    def test_all_high_risk_flags_true_returns_high(self):
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "multi_risk",
            "hr_recruitment_screening": True,
            "credit_worthiness": True,
            "law_enforcement": True,
            "is_safety_component": True,
            "affects_fundamental_rights": True,
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
    def test_high_risk_overrides_limited_risk_flags(self):
        """A system that triggers both HIGH and LIMITED flags must be HIGH."""
        payload = {
            **MINIMAL_PAYLOAD,
            "use_case_category": "hr_chatbot",
            "hr_recruitment_screening": True,   # HIGH trigger
            "interacts_with_humans": True,       # LIMITED trigger
        }
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
 
    @pytest.mark.parametrize(
        "payload_override,expected_status",
        [
            ({}, 200),                                          # all defaults → valid
            ({"use_case_category": ""}, 200),                  # empty string is still a str
            ({"is_safety_component": True}, 200),              # single HIGH flag
            ({"interacts_with_humans": True}, 200),            # single LIMITED flag
        ],
    )
    def test_edge_case_matrix(self, payload_override, expected_status):
        payload = {**MINIMAL_PAYLOAD, **payload_override}
 
        response = self.client.post(
            "/api/v1/classification/classify",
            json=payload,
        )
 
        assert response.status_code == expected_status