from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text

    # Assert that all required metrics are exposed
    assert "aegisai_guard_scans_total" in text
    assert "aegisai_rag_queries_total" in text
    assert "aegisai_ai_systems_total" in text
    assert "aegisai_http_request_duration_seconds" in text
