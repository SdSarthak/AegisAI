from app.modules.badge.badge_generator import generate_badge_svg


def test_generate_badge_svg_compliant():
    svg = generate_badge_svg("My AI", "high", "compliant")

    assert svg.startswith("<svg")
    assert 'fill="#4ade80"' in svg
    assert ">Compliant</text>" in svg


def test_generate_badge_svg_in_progress():
    svg = generate_badge_svg("Test System", "minimal", "in_progress")

    assert svg.startswith("<svg")
    assert 'fill="#facc15"' in svg
    assert ">In Progress</text>" in svg


def test_generate_badge_svg_contains_aegisai_label():
    svg = generate_badge_svg("Other System", "high", "compliant")

    assert ">AegisAI</text>" in svg

