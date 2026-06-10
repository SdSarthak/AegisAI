from dataclasses import dataclass
from typing import Literal

ComplianceStatus = Literal["missing", "partial", "done"]

@dataclass(frozen=True)
class RequirementItem:
    requirement: str
    article_reference: str
    status: ComplianceStatus
    action_needed: str

_HIGH_RISK_RULES = [
    ("Article 9", "Establish and maintain a risk management system covering all known and foreseeable risks.", "Implement a documented risk management system."),
    ("Article 10", "Ensure training, validation and testing datasets meet quality criteria.", "Document dataset lineage, quality criteria and bias-mitigation measures."),
    ("Article 11", "Prepare and maintain up-to-date technical documentation before market placement.", "Generate technical documentation (AegisAI → Documents → Generate)."),
    ("Article 12", "Implement automatic logging of events to ensure traceability.", "Enable automatic event logging and configure a log retention policy."),
    ("Article 13", "Provide clear instructions so deployers understand capabilities and risks.", "Produce user-facing documentation describing capabilities and limitations."),
    ("Article 14", "Design the system to allow human oversight and intervention.", "Implement human-in-the-loop controls and document the oversight mechanism."),
    ("Article 15", "Achieve appropriate accuracy, robustness, and cybersecurity resilience.", "Conduct adversarial testing and document performance metrics."),
    ("Article 43", "Complete the required conformity assessment before market placement.", "Complete and record the conformity assessment."),
    ("Article 49", "Register the high-risk AI system in the EU database.", "Register at https://ai-act-database.ec.europa.eu before go-live."),
    ("Article 72", "Establish a post-market monitoring plan proportional to risks.", "Define and activate a post-market monitoring plan."),
    ("Article 73", "Report serious incidents to authorities without undue delay.", "Set up an incident-reporting workflow with defined severity thresholds."),
]

_LIMITED_RISK_RULES = [
    ("Article 50(1)", "Inform users they are interacting with an AI system.", "Add a clear AI-disclosure notice in the UI or at the start of every session."),
    ("Article 50(2)", "Label AI-generated content as AI-generated.", "Implement watermarking or visible labelling of AI-generated output."),
]

_MINIMAL_RISK_RULES = [
    ("Recital 48 / Voluntary Code", "Consider voluntarily adopting the code of conduct for high-risk systems.", "Review and document your decision on adopting the voluntary code of conduct."),
]

_UNACCEPTABLE_RISK_RULES = [
    ("Article 5", "PROHIBITED: This system poses unacceptable risk. Deployment is prohibited.", "Immediately cease deployment and consult legal counsel."),
]

_RULES_BY_RISK = {
    "high": _HIGH_RISK_RULES,
    "limited": _LIMITED_RISK_RULES,
    "minimal": _MINIMAL_RISK_RULES,
    "unacceptable": _UNACCEPTABLE_RISK_RULES,
}

_COMPLIANCE_STATUS_MAP = {
    "compliant": "done",
    "in_progress": "partial",
    "under_review": "partial",
    "not_started": "missing",
    "non_compliant": "missing",
}

def evaluate_compliance(
    risk_level: str,
    questionnaire_responses: dict,
) -> list[RequirementItem]:
    """
    Return requirement items for the given risk level.
    Each requirement has its own individual status based on
    questionnaire_responses keys matching article references.
    """
    rules = _RULES_BY_RISK.get(risk_level.lower().strip(), [])
    results = []

    for article, description, action in rules:
        # Check individual requirement status from questionnaire responses
        req_key = article.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        req_status = questionnaire_responses.get(req_key, "missing")

        if req_status not in ("missing", "partial", "done"):
            req_status = "missing"

        results.append(RequirementItem(
            requirement=description,
            article_reference=article,
            status=req_status,
            action_needed="" if req_status == "done" else action,
        ))

    return results
