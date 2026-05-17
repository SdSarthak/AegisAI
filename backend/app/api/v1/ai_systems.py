from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.models.audit_log import AISystemAuditLog
from app.schemas.ai_system import (
    AISystemCreate,
    AISystemUpdate,
    AISystemResponse,
    BulkImportResponse,
    ComplianceStatusUpdateSchema,
)
from app.schemas.audit_log import AISystemAuditLogResponse
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    system_data: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
Create a new AI system for compliance tracking.

Args:
    system_data (AISystemCreate): Request payload containing
        AI system details such as name, description,
        version, use case, and sector.
    db (Session): Database session dependency used for
        persistence operations.
    current_user (User): Currently authenticated user.

Returns:
    AISystemResponse: The newly created AI system record.
"""
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
    """
Retrieve a paginated list of AI systems for the authenticated user.

Args:
    sort_by (Optional[str]): Field used for sorting results.
    order (Optional[str]): Sort direction, either ascending
        or descending.
    page (int): Page number for paginated results.
    limit (int): Maximum number of records per page.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    PaginatedResponse[AISystemResponse]: Paginated list of
        AI systems belonging to the authenticated user.

Raises:
    HTTPException: Raised when invalid sorting parameters
        are provided.
"""
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


@router.post("/import", response_model=BulkImportResponse)
def bulk_import_systems(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
Import multiple AI systems from a CSV file.

Args:
    file (UploadFile): CSV file containing AI system data.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    BulkImportResponse: Summary of successfully created
        systems and import errors.

Raises:
    HTTPException: Raised when the uploaded file format
        is invalid or CSV processing fails.
"""
    errors = []
    created_count = 0

    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV format: File must have .csv extension"
        )

    try:
        content = file.file.read()
        decoded_content = content.decode("utf-8")

        if not decoded_content.strip():
            return BulkImportResponse(created=0, errors=[])

        f = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(f)

        if not csv_reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV format: No headers found"
            )

        for row_num, row in enumerate(csv_reader, start=2):
            if not any(row.values()):
                continue

            name = row.get("name", "").strip()
            if not name:
                errors.append({"row": row_num, "error": "name is required"})
                continue

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

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )

    return BulkImportResponse(created=created_count, errors=errors)


@router.get("/export")
def export_ai_systems(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: minimal, limited, high, unacceptable"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
Export AI systems belonging to the authenticated user as a CSV file.

Args:
    risk_level (Optional[str]): Optional filter for AI
        system risk level.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    StreamingResponse: CSV file containing exported AI systems.

Raises:
    HTTPException: Raised when an invalid risk level
        filter is provided.
"""
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
    """
Retrieve audit history for a specific AI system.

Args:
    system_id (int): Unique identifier of the AI system.
    page (int): Page number for paginated results.
    limit (int): Maximum number of audit log entries per page.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    PaginatedResponse[AISystemAuditLogResponse]:
        Paginated audit history records for the AI system.

Raises:
    HTTPException: Raised when the requested AI system
        does not exist.
"""

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
    """
Retrieve details of a specific AI system.

Args:
    system_id (int): Unique identifier of the AI system.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    AISystemResponse: Details of the requested AI system.

Raises:
    HTTPException: Raised when the AI system is not found.
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
    return system


@router.put("/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: int,
    system_data: AISystemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
Update details of an existing AI system.

Args:
    system_id (int): Unique identifier of the AI system.
    system_data (AISystemUpdate): Updated AI system fields.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    AISystemResponse: Updated AI system information.

Raises:
    HTTPException: Raised when the AI system is not found.
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
    """
Delete an AI system belonging to the authenticated user.

Args:
    system_id (int): Unique identifier of the AI system.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    None: Endpoint returns no response body on successful deletion.

Raises:
    HTTPException: Raised when the AI system is not found.
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

    db.delete(system)
    db.commit()


@router.patch("/{system_id}/status", response_model=AISystemResponse)
def update_ai_system_status(
    system_id: int,
    payload: ComplianceStatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
Update the compliance status of an AI system.

Args:
    system_id (int): Unique identifier of the AI system.
    payload (ComplianceStatusUpdateSchema): Request payload
        containing the updated compliance status.
    db (Session): Database session dependency.
    current_user (User): Currently authenticated user.

Returns:
    AISystemResponse: Updated AI system information.

Raises:
    HTTPException: Raised when the AI system is not found.
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

    system.compliance_status = payload.compliance_status
    system._changed_by_id = current_user.id
    db.commit()
    db.refresh(system)
    return system

