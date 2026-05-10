from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel
from app.schemas.ai_system import (
    RiskClassificationRequest,
    RiskClassificationResponse,
)

router = APIRouter()


def classify_risk(data: RiskClassificationRequest) -> RiskClassificationResponse:
    """
    Classify the risk level of an AI system based on EU AI Act criteria.
    """

    reasons = []
    requirements = []
    risk_level = RiskLevel.MINIMAL
    confidence = 0.9

    # Check for HIGH risk systems
    high_risk_indicators = []

    if data.hr_recruitment_screening or data.hr_promotion_termination:
        high_risk_indicators.append("HR recruitment/management AI system")

        reasons.append(
            "AI systems used for recruitment or employment "
            "decisions are classified as HIGH risk under Annex III"
        )

        requirements.extend([
            "Implement risk management system",
            "Ensure data governance and quality",
            "Maintain technical documentation",
            "Enable record-keeping/logging",
            "Provide transparency to users",
            "Enable human oversight",
            "Ensure accuracy and robustness",
        ])

    if data.credit_worthiness or data.insurance_risk_assessment:
        high_risk_indicators.append(
            "Credit/insurance assessment AI"
        )

        reasons.append(
            "AI for creditworthiness or insurance risk "
            "assessment is HIGH risk under Annex III"
        )

    if data.is_safety_component:
        high_risk_indicators.append(
            "Safety component of a product"
        )

        reasons.append(
            "AI used as a safety component requires "
            "HIGH risk compliance"
        )

    if data.affects_fundamental_rights:
        high_risk_indicators.append(
            "Affects fundamental rights"
        )

        reasons.append(
            "System impacts fundamental rights"
        )

    if (
        data.law_enforcement
        or data.border_control
        or data.justice_system
    ):
        high_risk_indicators.append(
            "Law enforcement/justice system use"
        )

        reasons.append(
            "Use in law enforcement or justice is HIGH risk"
        )

    # Determine risk level
    if high_risk_indicators:
        risk_level = RiskLevel.HIGH

    elif (
        data.interacts_with_humans
        or data.emotion_recognition
        or data.generates_synthetic_content
    ):
        risk_level = RiskLevel.LIMITED

        if data.interacts_with_humans:
            reasons.append(
                "System interacts directly with humans"
            )

            requirements.append(
                "Inform users they are interacting with AI"
            )

        if data.emotion_recognition:
            reasons.append(
                "System uses emotion recognition"
            )

            requirements.append(
                "Inform subjects about emotion recognition"
            )

        if data.generates_synthetic_content:
            reasons.append(
                "System generates synthetic content"
            )

            requirements.append(
                "Label AI-generated content appropriately"
            )

    else:
        reasons.append(
            "System does not fall into high-risk "
            "or limited-risk categories"
        )

        requirements.append(
            "Voluntary codes of conduct encouraged"
        )

    # Generate next steps
    next_steps = []

    if risk_level == RiskLevel.HIGH:
        next_steps = [
            "Complete the risk assessment questionnaire",
            "Document technical specifications",
            "Implement risk management system",
            "Establish data governance procedures",
            "Set up human oversight mechanisms",
        ]

    elif risk_level == RiskLevel.LIMITED:
        next_steps = [
            "Implement transparency notices",
            "Document disclosure mechanisms",
            "Review user interaction points",
        ]

    else:
        next_steps = [
            "Consider voluntary compliance measures",
            "Monitor regulatory updates",
            "Document governance practices",
        ]

    return RiskClassificationResponse(
        risk_level=risk_level,
        confidence=confidence,
        reasons=reasons,
        requirements=requirements,
        next_steps=next_steps,
    )


@router.post(
    "/classify",
    response_model=RiskClassificationResponse,
)
def classify_ai_system(
    data: RiskClassificationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Classify an AI system's risk level.
    """

    return classify_risk(data)


@router.post(
    "/classify/{system_id}",
    response_model=RiskClassificationResponse,
)
def classify_and_save(
    system_id: int,
    data: RiskClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Classify an AI system and save the result.
    """

    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id,
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    # Perform classification
    result = classify_risk(data)

    # TODO:
    # Compliance score rollup integration pending.
    # RiskAssessment model dependency not yet available.

    db.commit()
    db.refresh(system)

    return result