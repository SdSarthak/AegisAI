"""NIST AI RMF 1.0 mapping constants.

This module maps EU AI Act risk tiers to the corresponding NIST AI RMF
functions, subcategories, and narrative metadata used in generated reports.
"""

from __future__ import annotations

EU_TO_NIST_MAPPING: dict[str, dict] = {
    "MINIMAL": {
        "primary_functions": ["GOVERN"],
        "subcategories": [
            "GOVERN 1.1 — Policies and procedures for AI risk management",
            "GOVERN 1.2 — Accountability structures are in place",
        ],
        "rationale": (
            "Minimal risk systems require basic governance policies "
            "to document AI use and maintain accountability."
        ),
        "nist_risk_tier": "Low",
    },
    "LIMITED": {
        "primary_functions": ["GOVERN", "MAP"],
        "subcategories": [
            "GOVERN 1.1 — Policies and procedures for AI risk management",
            "GOVERN 4.1 — Organizational teams are committed to risk management",
            "MAP 1.1 — Context is established for AI risk assessment",
            "MAP 1.5 — Organizational risk tolerances are defined",
            "MAP 2.1 — Scientific findings are reviewed for AI risks",
        ],
        "rationale": (
            "Limited risk systems require governance policies and risk "
            "context mapping, including transparency obligations."
        ),
        "nist_risk_tier": "Low-Medium",
    },
    "HIGH": {
        "primary_functions": ["GOVERN", "MAP", "MEASURE", "MANAGE"],
        "subcategories": [
            "GOVERN 1.1 — Policies and procedures for AI risk management",
            "GOVERN 1.7 — Risk management processes are integrated",
            "GOVERN 6.1 — Policies address AI supply chain risks",
            "MAP 1.1 — Context is established for AI risk assessment",
            "MAP 3.5 — Risks to critical systems are identified",
            "MAP 5.1 — Likelihood and magnitude of impacts are characterized",
            "MEASURE 1.1 — Risk metrics are defined and prioritized",
            "MEASURE 2.5 — AI system performance is monitored",
            "MEASURE 2.6 — Bias, fairness, and discrimination risks are evaluated",
            "MEASURE 4.1 — Metrics are monitored on an ongoing basis",
            "MANAGE 1.1 — Risks are prioritized by impact and likelihood",
            "MANAGE 2.2 — Risk response plans include human oversight",
            "MANAGE 3.1 — Risks are tracked and managed",
            "MANAGE 4.1 — Post-deployment risk monitoring is in place",
        ],
        "rationale": (
            "High-risk systems require comprehensive coverage across all "
            "four NIST AI RMF core functions with particular emphasis on "
            "measurement of bias/fairness and active risk management."
        ),
        "nist_risk_tier": "High",
    },
    "UNACCEPTABLE": {
        "primary_functions": ["GOVERN", "MAP", "MEASURE", "MANAGE"],
        "subcategories": [
            "GOVERN 1.1 — Policies must prohibit deployment of this system",
            "MAP 5.2 — Residual risks exceed acceptable thresholds",
            "MANAGE 1.3 — Risks are escalated for senior review",
            "MANAGE 2.4 — Deployment is halted pending remediation",
        ],
        "rationale": (
            "Unacceptable risk systems are prohibited under EU AI Act Article 5. "
            "Under NIST AI RMF, residual risks exceed all acceptable thresholds "
            "and deployment should be halted."
        ),
        "nist_risk_tier": "Critical",
    },
}

# NIST AI RMF Core Functions — brief descriptions for UI display
NIST_CORE_FUNCTIONS: dict[str, str] = {
    "GOVERN": (
        "Cultivate and implement an organizational culture of AI risk management, "
        "including policies, processes, and accountability."
    ),
    "MAP": (
        "Categorize AI risks based on context, including identifying AI system "
        "components, stakeholders, and potential impacts."
    ),
    "MEASURE": (
        "Analyze and assess AI risks using quantitative and qualitative methods, "
        "including bias detection and performance monitoring."
    ),
    "MANAGE": (
        "Prioritize and address AI risks through response plans, including "
        "mitigation strategies and post-deployment monitoring."
    ),
}

# Framework metadata
NIST_AI_RMF_METADATA = {
    "name": "NIST AI Risk Management Framework",
    "version": "1.0",
    "published": "January 2023",
    "publisher": "National Institute of Standards and Technology (NIST)",
    "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
    "scope": "US federal and enterprise AI governance",
}
