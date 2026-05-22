from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.models.compliance_requirement import ComplianceRequirement
from app.schemas.compliance_requirement import (
    ComplianceRequirementUpdate,
    ComplianceRequirementResponse,
)

router = APIRouter()


@router.get("/{system_id}/requirements", response_model=List[ComplianceRequirementResponse])
def get_requirements(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all compliance requirements for an AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()

    if not system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")

    return system.requirements


@router.patch("/{system_id}/requirements/{requirement_id}", response_model=ComplianceRequirementResponse)
def update_requirement(
    system_id: int,
    requirement_id: int,
    data: ComplianceRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update status of a compliance requirement."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()

    if not system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")

    requirement = db.query(ComplianceRequirement).filter(
        ComplianceRequirement.id == requirement_id,
        ComplianceRequirement.ai_system_id == system_id
    ).first()

    if not requirement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

    requirement.status = data.status
    db.commit()
    db.refresh(requirement)
    return requirement