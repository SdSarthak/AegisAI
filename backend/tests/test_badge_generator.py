from app.modules.badge.badge_generator import generate_badge_svg

def test_generate_badge_svg():
    svg = generate_badge_svg("My AI", "high", "compliant")

    assert svg.startswith("<svg")
    assert "AegisAI" in svg
    assert "Compliant" in svg
    assert "High Risk" in svg
    assert "</svg>" in svg