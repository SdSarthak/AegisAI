from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_api_service_rejects_empty_list_payloads():
    source = _read("frontend/src/services/api.ts")

    assert "function ensureListResponse" in source
    assert "response was empty or invalid." in source


def test_ai_systems_page_shows_retry_fallback():
    source = _read("frontend/src/pages/AISystems.tsx")

    assert "Unable to load AI systems" in source
    assert "refetch," in source
    assert "Retry" in source


def test_dashboard_shows_retry_fallback_for_invalid_api_payloads():
    source = _read("frontend/src/pages/Dashboard.tsx")

    assert "Unable to load dashboard" in source
    assert "refetchSystems()" in source
    assert "refetchDocuments()" in source


def test_documents_page_shows_retry_fallback_for_invalid_api_payloads():
    source = _read("frontend/src/pages/Documents.tsx")

    assert "Unable to load documents" in source
    assert "refetchDocuments()" in source
    assert "refetchSystems()" in source
    assert "hasError" in source
