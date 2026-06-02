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

    return classify_risk(data)    


@router.post("/classify/{system_id}", response_model=RiskClassificationResponse)
def classify_and_save(
    system_id: int,
    data: RiskClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

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

    return QUESTIONNAIRE_RISK_FACTORS

@router.post("/bulk", response_model=BulkClassificationResponse)
def bulk_classify_systems(
    request: BulkClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

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


