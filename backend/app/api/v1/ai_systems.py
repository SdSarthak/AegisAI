from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import csv
import io
import logging
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.schemas.ai_system import (
    AISystemCreate, 
    AISystemUpdate, 
    AISystemResponse,
    BulkImportResponse
)
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


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


def _process_import_task(
    content: bytes,
    user_id: int
):
    """Background task to process AI system imports."""
    from app.core.database import SessionLocal
    db_session = SessionLocal()
    try:
        decoded_content = content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded_content))
        
        for row_num, row in enumerate(csv_reader, start=2):
            if row_num - 2 >= settings.MAX_IMPORT_ROWS:
                logger.warning(f"Import truncated for user {user_id}: exceeded {settings.MAX_IMPORT_ROWS} rows")
                break
                
            name = row.get("name", "").strip()
            if not name:
                continue
            
            # Check for existing using local session
            existing = db_session.query(AISystem).filter(
                AISystem.owner_id == user_id,
                AISystem.name == name
            ).first()
            
            if existing:
                continue

            try:
                system = AISystem(
                    owner_id=user_id,
                    name=name,
                    description=row.get("description", "").strip() or None,
                    version=row.get("version", "").strip() or None,
                    use_case=row.get("use_case", "").strip() or None,
                    sector=row.get("sector", "").strip() or None
                )
                db_session.add(system)
            except Exception as e:
                logger.error(f"Error creating system in import: {str(e)}")
            
        db_session.commit()
    except Exception as e:
        logger.error(f"Error in bulk import background task: {str(e)}")
        db_session.rollback()
    finally:
        db_session.close()


@router.post("/import", response_model=BulkImportResponse)
async def bulk_import_systems(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Import AI systems from a CSV file.
    Processing is handled in the background to prevent DoS.
    """
    # 1. Enforce File Size Limit (DoS Mitigation)
    content = await file.read()
    if len(content) > settings.MAX_IMPORT_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_IMPORT_FILE_SIZE / 1024 / 1024}MB"
        )

    # 2. Basic Header Validation
    try:
        header_check = content[:1024].decode("utf-8")
        if "name" not in header_check.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV format: 'name' column is required"
            )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding. Please upload a UTF-8 encoded CSV."
        )

    # 3. Offload to Background Task
    background_tasks.add_task(_process_import_task, content, current_user.id)
    
    return BulkImportResponse(
        message="Bulk import started in the background. Systems will appear in your dashboard shortly.",
        created=0, 
        errors=[]
    )
