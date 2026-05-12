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
    "compliant": "#4ade80",  # green
    "in_progress": "#facc15",  # yellow
    "under_review": "#60a5fa",  # blue
    "non_compliant": "#f87171",  # red
    "not_started": "#9ca3af",  # gray
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
    color = STATUS_COLORS.get(compliance_status, STATUS_COLORS["not_started"])
    status_label = compliance_status.replace("_", " ").title()
    risk_label = RISK_LABELS.get(risk_level, "Unknown Risk") if risk_level else None

    # Text segments
    segments = [("AegisAI", "#555")]
    if risk_label:
        segments.append((risk_label, "#444"))
    segments.append((status_label, color))

    # Calculate widths
    char_width = 7
    padding = 12
    segment_widths = [len(text) * char_width + padding for text, _ in segments]
    total_width = sum(segment_widths)

    # Build SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">',
        f'<linearGradient id="b" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>',
        f'<mask id="a"><rect width="{total_width}" height="20" rx="3" fill="#fff"/></mask>',
        '<g mask="url(#a)">',
    ]

    current_x = 0
    for i, (text, bg_color) in enumerate(segments):
        w = segment_widths[i]
        svg.append(f'<path fill="{bg_color}" d="M{current_x} 0h{w}v20H{current_x}z"/>')
        current_x += w

    svg.append(f'<path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>')
    svg.append("</g>")
    svg.append(
        '<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">'
    )

    current_x = 0
    for i, (text, _) in enumerate(segments):
        w = segment_widths[i]
        center_x = current_x + w / 2
        svg.append(
            f'<text x="{center_x}" y="15" fill="#010101" fill-opacity=".3">{text}</text>'
        )
        svg.append(f'<text x="{center_x}" y="14">{text}</text>')
        current_x += w

    svg.append("</g>")
    svg.append("</svg>")

    return "".join(svg)
