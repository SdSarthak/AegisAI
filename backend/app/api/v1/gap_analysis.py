"""Gap Analysis API — compute and return compliance gaps for AI systems."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.schemas.integration import GapAnalysisResponse, ComplianceGap
from app.modules.gap_analysis import analyze_gaps, calculate_compliance_score

router = APIRouter()


@router.get("/{system_id}", response_model=GapAnalysisResponse)
def get_gap_analysis(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze compliance gaps for an AI system based on its risk level and questionnaire responses.
    
    Returns a detailed gap analysis with severity levels, recommendations, and affected articles.
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

    if not system.risk_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System has not been classified yet. Please run classification first.",
        )

    # Analyze gaps
    gaps_list = analyze_gaps(system.risk_level, system.questionnaire_responses or {})
    
    # Convert to schema objects
    gaps = [
        ComplianceGap(
            gap_type=gap["gap_type"],
            severity=gap["severity"],
            description=gap["description"],
            recommendation=gap["recommendation"],
            affected_articles=gap.get("affected_articles", []),
        )
        for gap in gaps_list
    ]

    # Calculate compliance score
    compliance_score = calculate_compliance_score(system.risk_level, gaps_list)

    # Build summary
    if system.risk_level.value == "unacceptable":
        summary = "This AI system is prohibited under EU AI Act Article 5. Deployment is not allowed."
    elif len(gaps) == 0:
        summary = f"This {system.risk_level.value.capitalize()}-risk system has no identified compliance gaps."
    else:
        summary = f"This {system.risk_level.value.capitalize()}-risk system has {len(gaps)} compliance gap(s) that need to be addressed."

    return GapAnalysisResponse(
        ai_system_id=system.id,
        risk_level=system.risk_level.value,
        compliance_status=system.compliance_status.value,
        overall_compliance_score=compliance_score,
        gaps=gaps,
        summary=summary,
        analysis_date=datetime.utcnow(),
    )
