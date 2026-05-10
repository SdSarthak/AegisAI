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
    """

    color = STATUS_COLORS.get(compliance_status, "#9ca3af") #(fallback to gray if unknown)

    status_label = compliance_status.replace("_", " ").title()

    risk_text = ""
    if risk_level:
        risk_text = f" ({RISK_LABELS.get(risk_level, risk_level.title())})"

    full_label = f"{status_label}{risk_text}"

    # SVG badge
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="20">
  <rect width="100" height="20" fill="#555"/>
  <rect x="100" width="120" height="20" fill="{color}"/>
  <text x="50" y="14" fill="#fff" font-size="11" font-family="sans-serif" text-anchor="middle">AegisAI</text>
  <text x="160" y="14" fill="#fff" font-size="11" font-family="sans-serif" text-anchor="middle">{full_label}</text>
</svg>'''

    return svg