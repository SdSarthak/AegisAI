"""
Compliance badge generator — produces SVG badges for public embedding.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (good first issue):
  - Implement `generate_badge_svg(system_name, risk_level, compliance_status)`
    that returns a valid SVG string.
  - Use the color map below to pick the right color per status.
  - The SVG should look like a standard shields.io-style badge:
    left label "AegisAI" | right value = compliance_status.
  - Acceptance criteria: calling generate_badge_svg() returns a string
    that starts with "<svg" and can be saved as a .svg file.
"""

STATUS_COLORS = {
    "compliant": "#4ade80",         # green
    "in_progress": "#facc15",       # yellow
    "under_review": "#60a5fa",      # blue
    "non_compliant": "#f87171",     # red
    "not_started": "#9ca3af",       # gray
}

RISK_LABELS = {
    "minimal": "Minimal Risk",
    "limited": "Limited Risk",
    "high": "High Risk",
    "unacceptable": "Unacceptable",
}


def generate_badge_svg(
    system_name: str,
    risk_level: str | None,
    compliance_status: str,
) -> str:
    """
    Generate an SVG compliance badge.

    Args:
        system_name: Name of the AI system.
        risk_level: One of minimal / limited / high / unacceptable, or None.
        compliance_status: One of the ComplianceStatus enum values.

    Returns:
        SVG string ready for serving with Content-Type: image/svg+xml.

    TODO (good first issue): implement the body of this function.
    Hint: build the SVG as an f-string using STATUS_COLORS and RISK_LABELS.
    """
    color = STATUS_COLORS.get(compliance_status, STATUS_COLORS["not_started"])
    status_label = compliance_status.replace("_", " ").title()

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="20">'
        f'<rect width="80" height="20" fill="#555"/>'
        f'<rect x="80" width="120" height="20" fill="{color}"/>'
        f'<text x="40" y="14" fill="#fff" font-size="11" font-family="sans-serif" text-anchor="middle">AegisAI</text>'
        f'<text x="140" y="14" fill="#fff" font-size="11" font-family="sans-serif" text-anchor="middle">{status_label}</text>'
        f'</svg>'
    )
