from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AI_SYSTEMS_PAGE = ROOT / "frontend" / "src" / "pages" / "AISystems.tsx"
API_SERVICE = ROOT / "frontend" / "src" / "services" / "api.ts"


def test_ai_systems_page_uses_server_side_filters_and_refetch_keys():
    content = AI_SYSTEMS_PAGE.read_text(encoding="utf-8")

    assert "systems.filter((system: AISystem)" not in content
    assert "search: searchTerm || undefined" in content
    assert "risk_level: riskFilter || undefined" in content
    assert "compliance_status: complianceFilter || undefined" in content
    assert "queryKey: ['ai-systems', sortBy, order, currentPage, searchTerm, riskFilter, complianceFilter]" in content
    assert "setCurrentPage(1)" in content
    assert "Page {currentPage} of {totalPages}" in content


def test_ai_systems_api_accepts_server_side_filter_params():
    content = API_SERVICE.read_text(encoding="utf-8")

    assert "search?: string" in content
    assert "risk_level?: string" in content
    assert "compliance_status?: string" in content
    assert "page?: number" in content
