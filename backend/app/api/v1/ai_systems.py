from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import csv
import io
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskAssessment
from app.core.scoring import compute_compliance_score
from app.schemas.ai_system import (
    AISystemCreate, 
    AISystemUpdate, 
    AISystemResponse,
    BulkImportResponse
)

router = APIRouter()


@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    system_data: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new AI system for compliance tracking."""
    ai_system = AISystem(
        owner_id=current_user.id,
        name=system_data.name,
        description=system_data.description,
        version=system_data.version,
        use_case=system_data.use_case,
        sector=system_data.sector
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)
    return ai_system


@router.get("/", response_model=List[AISystemResponse])
def list_ai_systems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all AI systems for the current user."""
    systems = db.query(AISystem).filter(AISystem.owner_id == current_user.id).all()
    return systems


@router.get("/{system_id}", response_model=AISystemResponse)
def get_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )
    return system


@router.put("/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: int,
    system_data: AISystemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )
    
    update_data = system_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(system, field, value)
    
    db.commit()
    db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )
    
    db.delete(system)
    db.commit()


@router.post("/import", response_model=BulkImportResponse)
async def bulk_import_systems(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import AI systems from a CSV file."""
    errors = []
    created_count = 0
    
    try:
        content = await file.read()
        decoded_content = content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded_content))
        
        for row_num, row in enumerate(csv_reader, start=2):
            if not row.get("name", "").strip():
                errors.append({"row": row_num, "error": "name is required"})
                continue
            
            name = row["name"].strip()
            
            existing = db.query(AISystem).filter(
                AISystem.owner_id == current_user.id,
                AISystem.name == name
            ).first()
            
            if existing:
                errors.append({"row": row_num, "error": f"duplicate name '{name}'"})
                continue
            
            try:
                ai_system = AISystem(
                    owner_id=current_user.id,
                    name=name,
                    description=row.get("description", "").strip() or None,
                    version=row.get("version", "").strip() or None,
                    use_case=row.get("use_case", "").strip() or None,
                    sector=row.get("sector", "").strip() or None
                )
                db.add(ai_system)
                created_count += 1
            except Exception as e:
                errors.append({"row": row_num, "error": str(e)})
        
        db.commit()
        
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )
    
    return BulkImportResponse(created=created_count, errors=errors)


@router.post("/{system_id}/recalculate-score")
def recalculate_score(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recalculate compliance score from the latest risk assessment."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()
    if not system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.ai_system_id == system_id)
        .order_by(RiskAssessment.assessed_at.desc())
        .first()
    )

    if assessment:
        system.compliance_score = compute_compliance_score(assessment)
        db.commit()
        return {"id": system_id, "assessment_id": assessment.id, "compliance_score": system.compliance_score}

    return {"id": system_id, "assessment_id": None, "compliance_score": system.compliance_score}
