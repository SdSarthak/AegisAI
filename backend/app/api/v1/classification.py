"""
Risk Classification API — EU AI Act risk level assessment for AI systems.

This module implements the risk classification logic based on the EU AI Act,
categorizing AI systems into four risk levels with corresponding compliance
requirements and next steps.

EU AI Act References:
    - Article 5: Prohibited AI practices (unacceptable risk - banned)
    - Article 6: Classification rules for high-risk AI systems
    - Article 52: Transparency obligations for limited-risk AI systems
    - Annex III: List of high-risk AI systems (recruitment, credit, law enforcement, etc.)

Risk Levels:
    - UNACCEPTABLE: Prohibited AI practices (social scoring, real-time biometric
      identification in public spaces) - banned under Article 5
    - HIGH: Systems affecting safety, fundamental rights, employment, credit,
      law enforcement, etc. - Articles 6-15, Annex III requirements
    - LIMITED: Chatbots, emotion recognition, synthetic content generation -
      transparency obligations under Article 52
    - MINIMAL: No specific requirements, voluntary compliance encouraged

Endpoints:
    POST /classify
        - Performs preliminary risk classification based on questionnaire responses
        - Returns risk level, confidence, reasons, requirements, and next steps
        - No database persistence

    POST /classify/{system_id}
        - Classifies an existing AI system and saves results to database
        - Updates AISystem.risk_level and AISystem.compliance_status
        - Creates RiskAssessment record with findings and recommendations

    POST /classify/bulk
        - Classifies multiple AI systems in one request (max batch processing)
        - Returns per-system results with partial failure details
        - Creates RiskAssessment records for each successfully classified system

    GET /classify/risk-factors
        - Returns static questionnaire metadata used in classification
        - Includes questions mapped to specific EU AI Act articles
        - Aligned with RiskClassificationRequest schema

Data Flow:
    Questionnaire Responses → RiskClassificationRequest → classify_risk()
                                                              ↓
                                              EU AI Act rules evaluation
                                                              ↓
                                            RiskClassificationResponse
                                                              ↓
                                    (Optionally) Persist to AISystem + RiskAssessment

Classification Logic (classify_risk function):
    - HIGH risk: Triggers from safety components, fundamental rights impact,
      HR systems (recruitment/promotion), credit/insurance, law enforcement,
      border control, or justice systems
    - LIMITED risk: Human interaction (chatbots), emotion recognition,
      synthetic content generation
    - MINIMAL risk: No triggers, default classification
    - Generates article-specific compliance requirements and next steps

Database Relationships:
    - AISystem: Stores risk_level and questionnaire_responses (JSON)
    - RiskAssessment: Creates assessment record with findings and recommendations
    - User: All endpoints require authentication, systems filtered by owner_id

Dependencies:
    - SQLAlchemy for database persistence (AISystem, RiskAssessment models)
    - Pydantic for request/response validation (RiskClassificationRequest/Response)
    - FastAPI for routing and dependency injection

Security:
    - All endpoints require authentication (get_current_user)
    - System access restricted to owner_id
    - Bulk classification validates ownership per system

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

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

router = APIRouter()

QUESTIONNAIRE_RISK_FACTORS: List[QuestionnaireRiskFactor] = [
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


@router.get("/risk-factors", response_model=List[QuestionnaireRiskFactor])
def get_questionnaire_risk_factors(
    current_user: User = Depends(get_current_user),
):
    """
    Return the static questionnaire metadata used by the risk classification flow.

    This does not query the database because these factors describe the
    classification rules themselves, not a user's saved questionnaire answers.
    Keep this list aligned with RiskClassificationRequest and classify_risk().
    """
    return QUESTIONNAIRE_RISK_FACTORS


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