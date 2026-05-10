import pytest
from app.modules.badge.badge_generator import generate_badge_svg, STATUS_COLORS

def test_generate_badge_svg_compliant():
    system_name = "Test AI"
    risk_level = "high"
    compliance_status = "compliant"
    
    svg = generate_badge_svg(system_name, risk_level, compliance_status)
    
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert f'fill="{STATUS_COLORS["compliant"]}"' in svg
    assert "Compliant" in svg
    assert "AegisAI" in svg

def test_generate_badge_svg_in_progress():
    svg = generate_badge_svg("My AI", None, "in_progress")
    assert f'fill="{STATUS_COLORS["in_progress"]}"' in svg
    assert "In Progress" in svg

def test_generate_badge_svg_unknown_status():
    # Should default to not_started color
    svg = generate_badge_svg("My AI", None, "unknown")
    assert f'fill="{STATUS_COLORS["not_started"]}"' in svg
    assert "Unknown" in svg
