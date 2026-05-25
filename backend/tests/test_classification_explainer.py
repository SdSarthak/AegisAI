import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.modules.explainer import explain_system_risk

def _make_client():
    from app.main import app
    from app.core.security import get_current_user

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"

    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)

class TestExplainerUnit:
    """Unit tests for explain_system_risk module core function."""

    def test_hr_screening_is_high_risk(self):
        desc = "An AI agent designed for CV screening, candidate ranking, and automatic recruitment evaluations."
        res = explain_system_risk(desc)
        
        assert res["risk_level"] == "HIGH"
        assert res["confidence"] >= 0.90
        assert "recruitment" in res["triggered_keywords"]
        assert "CV screening tools" in res["similar_systems"]
        
        # Verify relevant articles structure
        assert any(art["article"] == "EU AI Act Annex III, Point 4" for art in res["relevant_articles"])
        assert any(art["article"] == "EU AI Act Article 9" for art in res["relevant_articles"])
        
        # Verify recommendations
        assert "Generate Technical Documentation (required under Article 11)" in res["recommendations"]

    def test_social_scoring_is_unacceptable_risk(self):
        desc = "A government social scoring system designed to analyze personal profiles and restrict public access."
        res = explain_system_risk(desc)
        
        assert res["risk_level"] == "UNACCEPTABLE"
        assert res["confidence"] == 0.99
        assert "social scoring" in res["triggered_keywords"]
        assert any(art["article"] == "EU AI Act Article 5(1)(c)" for art in res["relevant_articles"])
        assert "Immediately cease development or deployment of this system." in res["recommendations"]

    def test_chatbot_is_limited_risk(self):
        desc = "A customer service chatbot designed to answer user inquiries and guide support."
        res = explain_system_risk(desc)
        
        assert res["risk_level"] == "LIMITED"
        assert "chatbot" in res["triggered_keywords"]
        assert any(art["article"] == "EU AI Act Article 52" for art in res["relevant_articles"])
        assert "Implement transparency notices to inform users they are interacting with AI (Article 52)" in res["recommendations"]

    def test_spam_filter_is_minimal_risk(self):
        desc = "A standard email spam filter algorithm using regex."
        res = explain_system_risk(desc)
        
        assert res["risk_level"] == "MINIMAL"
        assert res["confidence"] == 0.75
        assert any(art["article"] == "EU AI Act Article 95" for art in res["relevant_articles"])
        assert "Establish voluntary codes of ethical conduct for your AI system." in res["recommendations"]

    def test_empty_description_graceful_fallback(self):
        res = explain_system_risk("")
        assert res["risk_level"] == "MINIMAL"
        assert res["confidence"] == 0.75
        assert len(res["triggered_keywords"]) == 0


class TestExplainerIntegration:
    """Integration tests for POST /api/v1/classification/explain endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = _make_client()

    def test_explain_endpoint_successful(self):
        payload = {
            "description": "An AI recruitment system designed for screening applicant CVs."
        }
        response = self.client.post("/api/v1/classification/explain", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["risk_level"] == "HIGH"
        assert data["confidence"] >= 0.90
        assert isinstance(data["reasons"], list)
        assert len(data["reasons"]) > 0
        assert isinstance(data["relevant_articles"], list)
        assert len(data["relevant_articles"]) > 0
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
        assert "recruitment" in data["triggered_keywords"]

    def test_explain_endpoint_422_on_invalid_payload(self):
        # Description is required
        response = self.client.post("/api/v1/classification/explain", json={})
        assert response.status_code == 422
