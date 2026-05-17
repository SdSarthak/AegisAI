from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
import logging
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.models.audit_log import AISystemAuditLog
from app.models.notification import Notification, NotificationType
from app.schemas.ai_system import (
    AISystemCreate,
    AISystemUpdate,
    AISystemResponse,
    BulkImportResponse,
    ComplianceStatusUpdateSchema,
)
from app.core.config import settings
from app.schemas.audit_log import AISystemAuditLogResponse
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    system_data: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new AI system for compliance tracking."""
    ai_system = AISystem(
        owner_id=current_user.id,
        name=system_data.name,
        description=system_data.description,
        version=system_data.version,
        use_case=system_data.use_case,
        sector=system_data.sector,
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)
    return ai_system


_SORTABLE_FIELDS = {
    "name": AISystem.name,
    "risk_level": AISystem.risk_level,
    "compliance_score": AISystem.compliance_score,
    "created_at": AISystem.created_at,
}


@router.get("/", response_model=PaginatedResponse[AISystemResponse])
def list_ai_systems(
    sort_by: Optional[str] = Query("created_at", description="Sort field: name, risk_level, compliance_score, created_at"),
    order: Optional[str] = Query("desc", description="Sort direction: asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all AI systems for the current user, with optional sorting and pagination."""
    if sort_by not in _SORTABLE_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by '{sort_by}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}",
        )
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order. Use 'asc' or 'desc'.",
        )

    column = _SORTABLE_FIELDS[sort_by]
    direction = asc(column) if order == "asc" else desc(column)

    base_query = db.query(AISystem).filter(AISystem.owner_id == current_user.id)
    total = base_query.count()
    offset = (page - 1) * limit

    systems = (
        base_query
        .order_by(direction)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(items=systems, total=total, page=page, limit=limit)


def _process_import_task(
    content: bytes,
    user_id: int
):
    """Background task to process AI system imports."""
    from app.core.database import SessionLocal
    db_session = SessionLocal()
    created_count = 0
    errors = []
    
    try:
        decoded_content = content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded_content))
        
        for row_num, row in enumerate(csv_reader, start=2):
            if row_num - 2 >= settings.MAX_IMPORT_ROWS:
                logger.warning(f"Import truncated for user {user_id}: exceeded {settings.MAX_IMPORT_ROWS} rows")
                errors.append({"row": row_num, "error": f"Import truncated: exceeded {settings.MAX_IMPORT_ROWS} rows"})
                break
                
            if not any(row.values()):
                continue

            name = row.get("name", "").strip()
            if not name:
                errors.append({"row": row_num, "error": "name is required"})
                continue
            
            # Check for existing using local session
            existing = db_session.query(AISystem).filter(
                AISystem.owner_id == user_id,
                AISystem.name == name
            ).first()
            
            if existing:
                errors.append({"row": row_num, "error": f"duplicate name '{name}'"})
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
                created_count += 1
            except Exception as e:
                logger.error(f"Error creating system in import: {str(e)}")
                errors.append({"row": row_num, "error": str(e)})
            
        db_session.commit()
        
        # Create a notification for the user
        status_msg = f"Import completed: {created_count} systems created."
        if errors:
            status_msg += f" {len(errors)} errors found."
            
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORT_COMPLETED,
            title="Bulk Import Result",
            message=json.dumps({
                "summary": status_msg,
                "created": created_count,
                "errors": errors[:50]  # Limit to first 50 errors
            })
        )
        db_session.add(notification)
        db_session.commit()

    except Exception as e:
        logger.error(f"Error in bulk import background task: {str(e)}")
        db_session.rollback()
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORT_COMPLETED,
            title="Bulk Import Failed",
            message=json.dumps({"error": f"Internal process error: {str(e)}"})
        )
        db_session.add(notification)
        db_session.commit()
    finally:
        db_session.close()


@router.post("/import", response_model=BulkImportResponse)
def bulk_import_systems(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Import AI systems from a CSV file.
    Processing is handled in the background to prevent DoS.
    """
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV format: File must have .csv extension"
        )

    try:
        content = file.file.read()

        if len(content) > settings.MAX_IMPORT_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.MAX_IMPORT_FILE_SIZE // (1024 * 1024)}MB"
            )

        # Basic check for headers early
        try:
            sample = content[:1024].decode("utf-8")
            if "name" not in sample.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid CSV format: 'name' column is required"
                )
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be UTF-8 encoded CSV"
            )

        # Offload to Background Task
        background_tasks.add_task(_process_import_task, content, current_user.id)
        
        return BulkImportResponse(
            message="Bulk import started in the background. Systems will appear in your dashboard shortly.",
            created=0, 
            errors=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating import: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to initiate bulk import. Please check your file format."
        )


@router.get("/export")
def export_ai_systems(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: minimal, limited, high, unacceptable"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the authenticated user's AI systems registry as a CSV file."""
    query = db.query(AISystem).filter(AISystem.owner_id == current_user.id)

    if risk_level is not None:
        allowed = {"minimal", "limited", "high", "unacceptable"}
        if risk_level.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level '{risk_level}'. Allowed: {', '.join(sorted(allowed))}",
            )
        query = query.filter(AISystem.risk_level == risk_level.lower())

    systems = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "description", "version", "use_case", "sector",
        "risk_level", "compliance_status", "compliance_score", "created_at",
    ])
    for s in systems:
        writer.writerow([
            s.id,
            s.name,
            s.description or "",
            s.version or "",
            s.use_case or "",
            s.sector or "",
            s.risk_level.value if s.risk_level else "",
            s.compliance_status.value if s.compliance_status else "",
            s.compliance_score if s.compliance_score is not None else "",
            s.created_at.isoformat() if s.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"ai_systems.csv\""},
    )

@router.get(
    "/{system_id}/history",
    response_model=PaginatedResponse[AISystemAuditLogResponse],
)
def get_ai_system_history(
    system_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit history for a specific AI system."""

    system = (
        db.query(AISystem)
        .filter(
            AISystem.id == system_id,
            AISystem.owner_id == current_user.id,
        )
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    base_query = (
        db.query(AISystemAuditLog)
        .filter(AISystemAuditLog.ai_system_id == system_id)
    )

    total = base_query.count()

    logs = (
        base_query
        .order_by(AISystemAuditLog.changed_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{system_id}", response_model=AISystemResponse)
def get_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific AI system."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found"
        )
    return system


@router.put("/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: int,
    system_data: AISystemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an AI system."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found"
        )

    update_data = system_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(system, field, value)
    
    system._changed_by_id = current_user.id
    db.commit()
    db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an AI system."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found"
        )

    db.delete(system)
    db.commit()


@router.patch("/{system_id}/status", response_model=AISystemResponse)
def update_ai_system_status(
    system_id: int,
    payload: ComplianceStatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update only the compliance_status of an AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id,
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    system.compliance_status = payload.compliance_status
    system._changed_by_id = current_user.id
    db.commit()
    db.refresh(system)
    return system

