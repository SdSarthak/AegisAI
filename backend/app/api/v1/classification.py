from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel, RiskAssessment, ComplianceStatus
from app.schemas.ai_system import RiskClassificationRequest, RiskClassificationResponse

router = APIRouter()


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

    # Check for UNACCEPTABLE risk (Article 5 - Prohibited practices)
    # Social scoring, real-time biometric identification in public spaces, etc.
    # These are typically banned outright

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

    # Determine if HIGH risk
    if high_risk_indicators:
        risk_level = RiskLevel.HIGH

    # Check for LIMITED risk (Article 52 - Transparency obligations)
    elif (
        data.interacts_with_humans
        or data.emotion_recognition
        or data.generates_synthetic_content
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

    # MINIMAL risk - no specific requirements
    else:
        reasons.append("System does not fall into high-risk or limited-risk categories")
        requirements.append(
            "No mandatory requirements, but voluntary codes of conduct encouraged"
        )

    # Generate next steps based on risk level
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

    return RiskClassificationResponse(
        risk_level=risk_level,
        confidence=confidence,
        reasons=reasons,
        requirements=requirements,
        next_steps=next_steps,
    )


@router.post("/classify", response_model=RiskClassificationResponse)
def classify_ai_system(
    data: RiskClassificationRequest, current_user: User = Depends(get_current_user)
):
    """
    Classify an AI system's risk level based on EU AI Act criteria.
    This is a preliminary classification - full assessment requires more details.
    """
    return classify_risk(data)


@router.post("/classify/{system_id}", response_model=RiskClassificationResponse)
def classify_and_save(
    system_id: int,
    data: RiskClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Classify an AI system and save the result to the database.
    """
    # Get the AI system
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found"
        )

    # Perform classification
    result = classify_risk(data)

    # Update the AI system
    system.risk_level = result.risk_level
    system.compliance_status = ComplianceStatus.IN_PROGRESS
    system.questionnaire_responses = data.model_dump()

    # Create risk assessment record
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


@router.post("/bulk", response_model=BulkClassificationResponse)
def bulk_classify_systems(
    request: BulkClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Classify multiple AI systems in one request.
    Returns per-system classification results and partial failure details.
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
        system.questionnaire_responses = system.questionnaire_responses

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
