cat > backend/app/schemas/compliance.py << 'EOF'
from __future__ import annotations
from typing import Literal, List
from pydantic import BaseModel


class ComplianceRequirementItem(BaseModel):
    requirement: str
    article_reference: str
    status: Literal["missing", "partial", "done"]
    action_needed: str

    model_config = {"from_attributes": True}


class ComplianceGapResponse(BaseModel):
    system_id: int
    system_name: str
    risk_level: str
    compliance_status: str
    total_requirements: int
    done_count: int
    partial_count: int
    missing_count: int
    requirements: List[ComplianceRequirementItem]
EOF
code backend/app/api/v1/ai_systems.py
from app.schemas.compliance import ComplianceGapResponse, ComplianceRequirementItem
from app.models.ai_system import RiskLevel, ComplianceStatus
@router.get("/{system_id}", response_model=AISystemResponse)
# EU AI Act requirements per risk level
_EU_AI_ACT_REQUIREMENTS: dict[str, list[dict]] = {
    "high": [
        {
            "article_reference": "Article 9",
            "requirement": "Establish and maintain a risk management system covering all known and foreseeable risks throughout the lifecycle.",
        },
        {
            "article_reference": "Article 10",
            "requirement": "Ensure training, validation and testing datasets meet quality criteria: relevance, representativeness, and freedom from errors.",
        },
        {
            "article_reference": "Article 11",
            "requirement": "Prepare and maintain up-to-date technical documentation before placing the system on the market.",
        },
        {
            "article_reference": "Article 12",
            "requirement": "Implement automatic logging of events to ensure traceability of outputs throughout the system lifecycle.",
        },
        {
            "article_reference": "Article 13",
            "requirement": "Provide clear instructions for use so deployers understand the system's capabilities, limitations and risks.",
        },
        {
            "article_reference": "Article 14",
            "requirement": "Design the system to allow natural persons to effectively oversee and intervene during its operation.",
        },
        {
            "article_reference": "Article 15",
            "requirement": "Achieve appropriate levels of accuracy, robustness, and cybersecurity resilience against errors and adversarial attacks.",
        },
        {
            "article_reference": "Article 43",
            "requirement": "Complete the required conformity assessment procedure before placing the system on the market.",
        },
        {
            "article_reference": "Article 49",
            "requirement": "Register the high-risk AI system in the EU database before market placement.",
        },
        {
            "article_reference": "Article 72",
            "requirement": "Establish and implement a post-market monitoring plan proportional to the nature of risks.",
        },
        {
            "article_reference": "Article 73",
            "requirement": "Report serious incidents or malfunctions to relevant market-surveillance authorities without undue delay.",
        },
    ],
    "limited": [
        {
            "article_reference": "Article 50(1)",
            "requirement": "Inform users they are interacting with an AI system, unless this is obvious from context.",
        },
        {
            "article_reference": "Article 50(2)",
            "requirement": "Label AI-generated audio, image, video, or text content as AI-generated.",
        },
    ],
    "minimal": [
        {
            "article_reference": "Recital 48 / Voluntary Code",
            "requirement": "Consider voluntarily adopting the code of conduct designed for high-risk AI systems.",
        },
    ],
    "unacceptable": [
        {
            "article_reference": "Article 5",
            "requirement": "PROHIBITED: This system is classified as unacceptable risk. Deployment is prohibited under Article 5 of the EU AI Act.",
        },
    ],
}

_ACTION_NEEDED: dict[str, str] = {
    "Article 9": "Implement a documented risk management system and attach evidence to this record.",
    "Article 10": "Document dataset lineage, quality criteria and bias-mitigation measures.",
    "Article 11": "Generate technical documentation (AegisAI → Documents → Generate).",
    "Article 12": "Enable automatic event logging and configure a log retention policy.",
    "Article 13": "Produce user-facing documentation describing capabilities, limitations and intended use.",
    "Article 14": "Implement human-in-the-loop controls and document the oversight mechanism.",
    "Article 15": "Conduct adversarial testing, document performance metrics and apply cybersecurity measures.",
    "Article 43": "Complete and record the conformity assessment; retain the declaration of conformity.",
    "Article 49": "Register the system at https://ai-act-database.ec.europa.eu before go-live.",
    "Article 72": "Define and activate a post-market monitoring plan covering key risk indicators.",
    "Article 73": "Set up an incident-reporting workflow with defined severity thresholds and authority contacts.",
    "Article 50(1)": "Add a clear AI-disclosure notice in the UI or at the start of every session.",
    "Article 50(2)": "Implement watermarking or visible labelling of AI-generated output.",
    "Recital 48 / Voluntary Code": "Review and document your decision on adopting the voluntary code of conduct.",
    "Article 5": "Immediately cease deployment and consult legal counsel. Document the prohibition assessment.",
}


def _resolve_status(compliance_status: str) -> str:
    """Map ComplianceStatus enum value to missing/partial/done."""
    if compliance_status == "compliant":
        return "done"
    if compliance_status in ("in_progress", "under_review"):
        return "partial"
    return "missing"


@router.get("/{system_id}/gaps", response_model=ComplianceGapResponse)
def get_compliance_gaps(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return unmet EU AI Act requirements for a given AI system based on its risk level and compliance status."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    risk_level = system.risk_level.value if system.risk_level else "minimal"
    compliance_status_val = system.compliance_status.value if system.compliance_status else "not_started"

    item_status = _resolve_status(compliance_status_val)
    requirements_for_level = _EU_AI_ACT_REQUIREMENTS.get(risk_level, [])

    items: list[ComplianceRequirementItem] = []
    for req in requirements_for_level:
        action = "" if item_status == "done" else _ACTION_NEEDED.get(req["article_reference"], "")
        items.append(
            ComplianceRequirementItem(
                requirement=req["requirement"],
                article_reference=req["article_reference"],
                status=item_status,
                action_needed=action,
            )
        )

    return ComplianceGapResponse(
        system_id=system.id,
        system_name=system.name,
        risk_level=risk_level,
        compliance_status=compliance_status_val,
        total_requirements=len(items),
        done_count=sum(1 for i in items if i.status == "done"),
        partial_count=sum(1 for i in items if i.status == "partial"),
        missing_count=sum(1 for i in items if i.status == "missing"),
        requirements=items,
    )
git checkout -b feat/compliance-gaps-endpoint
git add backend/app/api/v1/ai_systems.py backend/app/schemas/compliance.py
git commit -m "feat: add EU AI Act compliance gaps endpoint (closes #49)"
git push origin feat/compliance-gaps-endpoint
cd AegisAI
git status
git status
pwd
cd AgeisAI
pwd
