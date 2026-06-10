from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.modules.compliance.nist_mapping import EU_TO_NIST_MAPPING
from app.schemas.ai_system import NISTMapping
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel, RiskAssessment, ComplianceStatus
from app.schemas.ai_system import (
    RiskClassificationRequest,
    RiskClassificationResponse,
    QuestionnaireRiskFactor,
)
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.modules.explainer.engine import explain_risk

router = APIRouter()

QUESTIONNAIRE_RISK_FACTORS: List[QuestionnaireRiskFactor] = [
    # Article 5 — Prohibited practices (checked first)
    QuestionnaireRiskFactor(
        id="social_scoring",
        question="Is the system used by a public authority to evaluate or classify individuals based on their social behaviour or personal characteristics?",
        article="Article 5(1)(c)",
        triggers_level=RiskLevel.UNACCEPTABLE,
    ),
    QuestionnaireRiskFactor(
        id="realtime_biometric_public",
        question="Does the system perform real-time remote biometric identification of individuals in publicly accessible spaces?",
        article="Article 5(1)(h)",
        triggers_level=RiskLevel.UNACCEPTABLE,
    ),
    QuestionnaireRiskFactor(
        id="biometric_categorisation",
        question="Does the system categorise individuals based on biometric data to infer sensitive attributes such as race, political opinions, religion, or sexual orientation?",
        article="Article 5(1)(g)",
        triggers_level=RiskLevel.UNACCEPTABLE,
    ),
    QuestionnaireRiskFactor(
        id="subliminal_manipulation",
        question="Does the system use subliminal techniques or manipulative methods that impair a person's ability to make free decisions, causing them harm?",
        article="Article 5(1)(a)",
        triggers_level=RiskLevel.UNACCEPTABLE,
    ),
    QuestionnaireRiskFactor(
        id="exploits_vulnerable_groups",
        question="Does the system exploit vulnerabilities of specific groups such as children, elderly, or persons with disabilities to distort their behaviour in a harmful way?",
        article="Article 5(1)(b)",
        triggers_level=RiskLevel.UNACCEPTABLE,
    ),
    QuestionnaireRiskFactor(
        id="is_safety_component",
        question="Is the AI system used as a safety component of a product or system?",
        article="Article 6(1)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="affects_fundamental_rights",
        question="Can the AI system affect fundamental rights such as employment, education, essential services, or access to opportunities?",
        article="Article 6(2)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="uses_biometric_data",
        question="Does the system use biometric data for identification, verification, or categorization?",
        article="Annex III",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="makes_automated_decisions",
        question="Does the system make automated decisions without meaningful human review?",
        article="Article 6 / Annex III context",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="hr_recruitment_screening",
        question="Is the system used for recruitment, CV screening, candidate filtering, or candidate ranking?",
        article="Annex III point 4(a)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="hr_promotion_termination",
        question="Is the system used for promotion, termination, task allocation, performance evaluation, or employment-related decisions?",
        article="Annex III point 4(b)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="credit_worthiness",
        question="Is the system used to evaluate creditworthiness or determine access to financial resources?",
        article="Annex III point 5(b)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="insurance_risk_assessment",
        question="Is the system used for insurance risk assessment, pricing, or eligibility decisions?",
        article="Annex III point 5(c)",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="law_enforcement",
        question="Is the system used by or for law enforcement purposes?",
        article="Annex III point 6",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="border_control",
        question="Is the system used for migration, asylum, or border control management?",
        article="Annex III point 7",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="justice_system",
        question="Is the system used to assist judicial authorities or influence legal outcomes?",
        article="Annex III point 8",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="education_vocational_training",
        question="Is the system used to determine access to or assign natural persons to educational and vocational training institutions?",
        article="Annex III point 3",
        triggers_level=RiskLevel.HIGH,
    ),
    QuestionnaireRiskFactor(
        id="interacts_with_humans",
        question="Does the system directly interact with humans, such as a chatbot or virtual assistant?",
        article="Article 52(1)",
        triggers_level=RiskLevel.LIMITED,
    ),
    QuestionnaireRiskFactor(
        id="generates_synthetic_content",
        question="Does the system generate synthetic or manipulated audio, image, video, or text content?",
        article="Article 52(3)",
        triggers_level=RiskLevel.LIMITED,
    ),
    QuestionnaireRiskFactor(
        id="emotion_recognition",
        question="Does the system perform emotion recognition?",
        article="Article 52(3)",
        triggers_level=RiskLevel.LIMITED,
    ),
    QuestionnaireRiskFactor(
        id="biometric_categorization",
        question="Does the system perform biometric categorization?",
        article="Article 52 / Annex III context",
        triggers_level=RiskLevel.LIMITED,
    ),
]


class BulkClassificationItem(BaseModel):
    system_id: int
    classification: Optional[RiskClassificationResponse] = None
    error: Optional[str] = None


class BulkClassificationRequest(BaseModel):
    system_ids: List[int]


class BulkClassificationResponse(BaseModel):
    results: List[BulkClassificationItem]


def classify_risk(data: RiskClassificationRequest) -> RiskClassificationResponse:
    """
    Classify the risk level of an AI system based on EU AI Act criteria.
    """
    reasons = []
    requirements = []
    risk_level = RiskLevel.MINIMAL
    confidence = 0.9

    # ----------------------------------------------------------------
    # Article 5 — Prohibited practices (UNACCEPTABLE risk)
    # These must be checked first — they override all other categories
    # ----------------------------------------------------------------
    prohibited_flags = {
        "social_scoring": "Social scoring by public authorities (Article 5(1)(c))",
        "realtime_biometric_public": "Real-time remote biometric identification in public spaces (Article 5(1)(h))",
        "biometric_categorisation": "Biometric categorisation using sensitive attributes (Article 5(1)(g))",
        "subliminal_manipulation": "Subliminal manipulation of behaviour (Article 5(1)(a))",
        "exploits_vulnerable_groups": "Exploitation of vulnerabilities of specific groups (Article 5(1)(b))",
    }

    triggered_prohibitions = [
        label for field, label in prohibited_flags.items()
        if getattr(data, field, False)
    ]

    if triggered_prohibitions:
        risk_level = RiskLevel.UNACCEPTABLE
        reasons.extend(triggered_prohibitions)
        requirements.append(
            "This AI system is prohibited under Article 5 of the EU AI Act "
            "and must not be placed on the market, put into service, or used."
        )
        return RiskClassificationResponse(
            risk_level=risk_level,
            confidence=0.99,
            reasons=reasons,
            requirements=requirements,
            next_steps=[
                "Immediately cease development or deployment of this system.",
                "Consult legal counsel regarding Article 5 compliance obligations.",
                "Review whether any Article 5 exceptions apply to your use case.",
            ],
        )
    
    # Check for HIGH risk (Article 6 + Annex III)
    high_risk_indicators = []

    # HR and recruitment AI (Annex III, point 4)
    if data.hr_recruitment_screening or data.hr_promotion_termination:
        high_risk_indicators.append("HR recruitment/management AI system")
        reasons.append(
            "AI systems used for recruitment, CV screening, or employment decisions are classified as HIGH risk under Annex III"
        )
        requirements.extend(
            [
                "Implement risk management system (Article 9)",
                "Ensure data governance and quality (Article 10)",
                "Maintain technical documentation (Article 11)",
                "Enable record-keeping/logging (Article 12)",
                "Provide transparency to users (Article 13)",
                "Enable human oversight (Article 14)",
                "Ensure accuracy, robustness, cybersecurity (Article 15)",
            ]
        )

    # Credit and insurance (Annex III, point 5)
    if data.credit_worthiness or data.insurance_risk_assessment:
        high_risk_indicators.append("Credit/insurance assessment AI")
        reasons.append(
            "AI for creditworthiness or insurance risk assessment is HIGH risk under Annex III"
        )

    # Education and vocational training (Annex III, point 3)
    if data.education_vocational_training:
        high_risk_indicators.append("Education/vocational training AI")
        reasons.append(
            "AI used for determining access to education or vocational training is HIGH risk under Annex III"
        )

    # Safety component
    if data.is_safety_component:
        high_risk_indicators.append("Safety component of a product")
        reasons.append("AI used as a safety component requires HIGH risk compliance")

    # Fundamental rights impact
    if data.affects_fundamental_rights:
        high_risk_indicators.append("Affects fundamental rights")
        reasons.append(
            "System impacts fundamental rights (employment, education, essential services)"
        )

    # Law enforcement, border control, justice
    if data.law_enforcement or data.border_control or data.justice_system:
        high_risk_indicators.append("Law enforcement/justice system use")
        reasons.append(
            "Use in law enforcement, border control, or justice is HIGH risk"
        )

    # Biometric data usage (Annex III)           
    if data.uses_biometric_data:
        high_risk_indicators.append("Uses biometric data")
        reasons.append(
            "System uses biometric data for identification, verification, or categorization (Annex III)"
        )

    # Automated decisions without human review (Article 6 / Annex III)
    if data.makes_automated_decisions:
        high_risk_indicators.append("Automated decisions without human review")
        reasons.append(
            "System makes automated decisions without meaningful human oversight (Article 6)"
        )    

    # Determine if HIGH risk
    if high_risk_indicators:
        risk_level = RiskLevel.HIGH

    elif (
        data.interacts_with_humans
        or data.emotion_recognition
        or data.generates_synthetic_content
        or data.biometric_categorization
    ):
        risk_level = RiskLevel.LIMITED
        if data.interacts_with_humans:
            reasons.append("System interacts directly with humans (e.g., chatbot)")
            requirements.append(
                "Inform users they are interacting with AI (Article 52)"
            )
        if data.emotion_recognition:
            reasons.append("System uses emotion recognition")
            requirements.append("Inform subjects about emotion recognition system")
        if data.generates_synthetic_content:
            reasons.append("System generates synthetic/manipulated content")
            requirements.append("Label AI-generated content appropriately")
        if data.biometric_categorization:   
            reasons.append("System performs biometric categorization")
            requirements.append(
                "Inform subjects about biometric categorization (Article 52)"
            )

    else:
        reasons.append("System does not fall into high-risk or limited-risk categories")
        requirements.append(
            "No mandatory requirements, but voluntary codes of conduct encouraged"
        )

    next_steps = []
    if risk_level == RiskLevel.HIGH:
        next_steps = [
            "Complete the full risk assessment questionnaire",
            "Document your AI system's technical specifications",
            "Implement a risk management system",
            "Establish data governance procedures",
            "Set up human oversight mechanisms",
            "Prepare conformity assessment documentation",
        ]
    elif risk_level == RiskLevel.LIMITED:
        next_steps = [
            "Implement transparency notices for users",
            "Document your disclosure mechanisms",
            "Review interaction points with users",
        ]
    else:
        next_steps = [
            "Consider voluntary compliance measures",
            "Monitor regulatory updates",
            "Document your AI governance practices",
        ]

    # Lookup NIST mapping once for the determined risk level
    nist_data = EU_TO_NIST_MAPPING.get(risk_level.value.upper())
    nist_mapping = NISTMapping(**nist_data) if nist_data else None
    
    return RiskClassificationResponse(
        risk_level=risk_level,
        confidence=confidence if not triggered_prohibitions else 0.99,
        reasons=reasons,
        requirements=requirements,
        next_steps=next_steps,
        nist_mapping=nist_mapping,
    )


@router.post("/classify", response_model=RiskClassificationResponse)
def classify_ai_system(
    data: RiskClassificationRequest, current_user: User = Depends(get_current_user)
):
    """Classify an AI system's risk level from questionnaire answers.

    Args:
        data: Structured questionnaire payload describing the AI system.
        current_user: Authenticated user requesting the classification.

    Returns:
        RiskClassificationResponse with the computed risk tier, rationale,
        requirements, and suggested next steps.
    """
    return classify_risk(data)    


@router.post("/classify/{system_id}", response_model=RiskClassificationResponse)
def classify_and_save(
    system_id: int,
    data: RiskClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Classify an AI system and persist the result.

    Args:
        system_id: ID of the AI system to classify.
        data: Structured questionnaire payload describing the AI system.
        db: Active database session.
        current_user: Authenticated user who owns the target system.

    Returns:
        RiskClassificationResponse representing the saved assessment.

    Raises:
        HTTPException: If the AI system does not exist or does not belong to
            the authenticated user.
    """
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found"
        )

    result = classify_risk(data)

    system.risk_level = result.risk_level
    system.compliance_status = ComplianceStatus.IN_PROGRESS
    system.questionnaire_responses = data.model_dump()

    assessment = RiskAssessment(
        ai_system_id=system.id,
        assessment_type="initial",
        risk_level=result.risk_level,
        findings=[{"type": "classification", "reasons": result.reasons}],
        recommendations=[
            {"requirements": result.requirements, "next_steps": result.next_steps}
        ],
        overall_score=70 if result.risk_level == RiskLevel.MINIMAL else 30,
    )
    db.add(assessment)
    db.commit()
    db.refresh(system)

    return result


@router.get("/risk-factors", response_model=List[QuestionnaireRiskFactor])
def get_questionnaire_risk_factors(
    current_user: User = Depends(get_current_user),
):
    """Return the static questionnaire metadata used by the classifier.

    Args:
        current_user: Authenticated user requesting the metadata.

    Returns:
        The list of questionnaire risk factors used by the classification UI.
    """
    return QUESTIONNAIRE_RISK_FACTORS


@router.post("/bulk", response_model=BulkClassificationResponse)
def bulk_classify_systems(
    request: BulkClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Classify multiple saved AI systems in a single request.

    Args:
        request: Payload containing the AI system IDs to classify.
        db: Active database session.
        current_user: Authenticated user who owns the systems.

    Returns:
        BulkClassificationResponse with per-system classification results.
    """
    results: List[BulkClassificationItem] = []

    for system_id in request.system_ids:
        system = db.query(AISystem).filter(
            AISystem.id == system_id,
            AISystem.owner_id == current_user.id
        ).first()

        if not system:
            results.append(
                BulkClassificationItem(
                    system_id=system_id,
                    error="AI system not found"
                )
            )
            continue

        if not system.questionnaire_responses:
            results.append(
                BulkClassificationItem(
                    system_id=system_id,
                    error="Questionnaire responses missing"
                )
            )
            continue

        try:
            classification_data = RiskClassificationRequest(**system.questionnaire_responses)
        except Exception as exc:
            results.append(
                BulkClassificationItem(
                    system_id=system_id,
                    error=f"Invalid questionnaire responses: {exc}"
                )
            )
            continue

        result = classify_risk(classification_data)
        system.risk_level = result.risk_level
        system.compliance_status = ComplianceStatus.IN_PROGRESS
        system.questionnaire_responses = classification_data.model_dump()

        assessment = RiskAssessment(
            ai_system_id=system.id,
            assessment_type="bulk",
            risk_level=result.risk_level,
            findings=[{"type": "classification", "reasons": result.reasons}],
            recommendations=[{"requirements": result.requirements, "next_steps": result.next_steps}],
            overall_score=70 if result.risk_level == RiskLevel.MINIMAL else 30
        )
        db.add(assessment)

        results.append(
            BulkClassificationItem(
                system_id=system_id,
                classification=result
            )
        )

    db.commit()
    return BulkClassificationResponse(results=results)


@router.post("/explain", response_model=ExplainResponse)
def explain_ai_system_risk(
    data: ExplainRequest,
    current_user: User = Depends(get_current_user),
):
    """Explain an AI system's risk classification from a text description.

    Args:
        data: Plain-text description and context used to generate the
            explanation.
        current_user: Authenticated user requesting the explanation.

    Returns:
        ExplainResponse with the generated explanation payload.
    """
    return explain_risk(data)
