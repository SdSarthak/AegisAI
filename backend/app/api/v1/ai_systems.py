from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import csv
import io

from app.core.csv_utils import sanitize_csv_field
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.ai_system import AISystem, ComplianceStatus, RiskAssessment
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
from app.modules.compliance.eu_ai_act import evaluate_compliance
from app.schemas.compliance import ComplianceGapResponse, ComplianceRequirementItem

router = APIRouter()


def _read_upload_file(file: UploadFile, max_bytes: int) -> str:
    """Read a CSV upload with a hard byte cap."""

    file.file.seek(0)
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = file.file.read(min(1024 * 1024, max_bytes + 1 - total_bytes))
        if not chunk:
            break

        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"CSV upload exceeds the maximum size of {max_bytes // (1024 * 1024)}MB."
                ),
            )

        chunks.append(chunk)

    try:
        return b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV",
        )


def _process_import_rows(
    csv_reader: csv.DictReader,
    db: Session,
    current_user: User,
    max_rows: int,
) -> tuple[int, list[dict[str, object]]]:
    """Import CSV rows up to the configured maximum."""

    errors: list[dict[str, object]] = []
    created_count = 0
    seen_names: set[str] = set()

    for row_num, row in enumerate(csv_reader, start=2):
        if row_num - 1 > max_rows:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"CSV upload exceeds the maximum row count of {max_rows}."
                ),
            )

        if not any(row.values()):
            continue

        name = row.get("name", "").strip()
        if not name:
            errors.append({"row": row_num, "error": "name is required"})
            continue

        # Check for duplicates within the same uploaded CSV first
        if name in seen_names:
            errors.append({"row": row_num, "error": f"duplicate name '{name}' in uploaded file"})
            continue

        existing = db.query(AISystem).filter(
            AISystem.owner_id == current_user.id,
            AISystem.name == name,
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
            seen_names.add(name)
        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    return created_count, errors


@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    system_data: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new AI system for compliance tracking."""
    # Enforce per-user uniqueness of AI system names to match bulk import behavior
    existing = db.query(AISystem).filter(
        AISystem.owner_id == current_user.id,
        AISystem.name == system_data.name,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI system with name '{system_data.name}' already exists",
        )

    ai_system = AISystem(
        owner_id=current_user.id,
        name=system_data.name,
        description=system_data.description,
        version=system_data.version,
        use_case=system_data.use_case,
        sector=system_data.sector,
    )
    db.add(ai_system)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI system with name '{system_data.name}' already exists",
        )
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
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: minimal, limited, high, unacceptable"),
    compliance_status: Optional[str] = Query(None, description="Filter by compliance status: not_started, in_progress, under_review, compliant, non_compliant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's AI systems with sorting and pagination."""
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

    if search:
        search_filter = f"%{search}%"
        base_query = base_query.filter(
            (AISystem.name.ilike(search_filter)) |
            (AISystem.description.ilike(search_filter))
        )

    if risk_level:
        allowed_risk = {"minimal", "limited", "high", "unacceptable"}
        if risk_level.lower() not in allowed_risk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level '{risk_level}'. Allowed: {', '.join(sorted(allowed_risk))}",
            )
        base_query = base_query.filter(AISystem.risk_level == risk_level.lower())

    if compliance_status:
        allowed_compliance = {"not_started", "in_progress", "under_review", "compliant", "non_compliant"}
        if compliance_status.lower() not in allowed_compliance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid compliance_status '{compliance_status}'. Allowed: {', '.join(sorted(allowed_compliance))}",
            )
        base_query = base_query.filter(AISystem.compliance_status == compliance_status.lower())

    total = base_query.count()

    systems = (
        base_query
        .order_by(direction)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(items=systems, total=total, skip=skip, limit=limit)


@router.post("/import", response_model=BulkImportResponse)
def bulk_import_systems(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import AI systems from a CSV file."""
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV format: File must have .csv extension"
        )

    try:
        decoded_content = _read_upload_file(
            file,
            settings.AI_SYSTEM_BULK_IMPORT_MAX_BYTES,
        )

        if not decoded_content.strip():
            return BulkImportResponse(created=0, errors=[])

        f = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(f)

        if not csv_reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV format: No headers found"
            )

        created_count, errors = _process_import_rows(
            csv_reader,
            db,
            current_user,
            settings.AI_SYSTEM_BULK_IMPORT_MAX_ROWS,
        )

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


def _latest_risk_assessment(db: Session, system_id: int) -> RiskAssessment | None:
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.ai_system_id == system_id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())
        .first()
    )


def _export_row(system: AISystem, valid_until: datetime | None) -> dict[str, object]:
    risk_level = system.risk_level.value if system.risk_level else ""
    compliance_status = (
        system.compliance_status.value if system.compliance_status else ""
    )

    return {
        "id": system.id,
        "name": system.name,
        "description": system.description or "",
        "sector": system.sector or "",
        "use_case": system.use_case or "",
        "risk_classification": risk_level,
        "risk_level": risk_level,
        "compliance_status": compliance_status,
        "compliance_score": system.compliance_score,
        "valid_until": valid_until.isoformat() if valid_until else None,
        "created_at": system.created_at.isoformat() if system.created_at else None,
        "updated_at": system.updated_at.isoformat() if system.updated_at else None,
    }


@router.get("/export")
def export_ai_systems(
    format: str = Query("csv", description="Export format: csv or json"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: minimal, limited, high, unacceptable"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the authenticated user's AI systems registry as CSV or JSON."""
    query = db.query(AISystem).filter(AISystem.owner_id == current_user.id)

    if risk_level is not None:
        allowed = {"minimal", "limited", "high", "unacceptable"}
        if risk_level.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level '{risk_level}'. Allowed: {', '.join(sorted(allowed))}",
            )
        query = query.filter(AISystem.risk_level == risk_level.lower())

    export_format = format.lower()
    allowed_formats = {"csv", "json"}
    if export_format not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{format}'. Allowed: csv, json",
        )

    systems = query.order_by(AISystem.created_at.desc()).yield_per(100)

    if export_format == "json":
        payload: list[dict[str, object]] = []
        for system in systems:
            assessment = _latest_risk_assessment(db, system.id)
            payload.append(_export_row(system, assessment.valid_until if assessment else None))

        filename = "ai_systems.json"
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    headers = [
        "id",
        "name",
        "description",
        "sector",
        "use_case",
        "risk_classification",
        "risk_level",
        "compliance_status",
        "compliance_score",
        "valid_until",
        "created_at",
        "updated_at",
    ]

    def generate_csv():
        yield "\ufeff"
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for system in systems:
            assessment = _latest_risk_assessment(db, system.id)
            row = _export_row(system, assessment.valid_until if assessment else None)
            writer.writerow([
                sanitize_csv_field(str(row["id"])),
                sanitize_csv_field(str(row["name"])),
                sanitize_csv_field(str(row["description"])),
                sanitize_csv_field(str(row["sector"])),
                sanitize_csv_field(str(row["use_case"])),
                sanitize_csv_field(str(row["risk_classification"])),
                sanitize_csv_field(str(row["risk_level"])),
                sanitize_csv_field(str(row["compliance_status"])),
                row["compliance_score"] if row["compliance_score"] is not None else "",
                sanitize_csv_field(str(row["valid_until"] or "")),
                sanitize_csv_field(str(row["created_at"] or "")),
                sanitize_csv_field(str(row["updated_at"] or "")),
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    filename = "ai_systems.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{system_id}/history",
    response_model=PaginatedResponse[AISystemAuditLogResponse],
)
def get_ai_system_history(
    system_id: int,
    order: Optional[str] = Query("desc", description="Sort direction for changed_at: asc, desc"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return paginated audit history for a specific AI system."""
    
    # 1. Validate sorting parameter
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order parameter. Use 'asc' or 'desc'.",
        )

    # 2. Verify AI system exists and belongs to the authenticated user
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

    # 3. Build the base audit log query
    base_query = (
        db.query(AISystemAuditLog)
        .filter(AISystemAuditLog.ai_system_id == system_id)
    )

    # 4. Calculate total records for pagination
    total = base_query.count()

    # 5. Apply dynamic sorting based on input
    direction = asc(AISystemAuditLog.changed_at) if order == "asc" else desc(AISystemAuditLog.changed_at)

    # 6. Apply pagination and execute
    logs = (
        base_query
        .order_by(direction)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=logs,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{system_id}", response_model=AISystemResponse)
def get_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single AI system owned by the current user."""
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


@router.post("/{system_id}/clone", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def clone_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clone an existing AI system with a '(copy)' suffix and reset compliance status."""
    original = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()

    if not original:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )

    cloned = AISystem(
        owner_id=current_user.id,
        name=f"{original.name} (copy)",
        description=original.description,
        version=original.version,
        use_case=original.use_case,
        sector=original.sector,
        compliance_status=ComplianceStatus.NOT_STARTED,
    )

    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    return cloned


@router.put("/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: int,
    system_data: AISystemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing AI system."""
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
    """Delete an AI system owned by the current user."""
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
    """Update only the compliance status of an AI system."""
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




@router.get("/{system_id}/gaps", response_model=ComplianceGapResponse)
def get_compliance_gaps(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return unmet EU AI Act requirements for a given AI system based on its risk level."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    risk_level = system.risk_level.value if system.risk_level else "minimal"
    questionnaire_responses = system.questionnaire_responses or {}

    all_items = evaluate_compliance(risk_level, questionnaire_responses)

    return ComplianceGapResponse(
        system_id=system.id,
        system_name=system.name,
        risk_level=risk_level,
        compliance_status=system.compliance_status.value if system.compliance_status else "not_started",
        total_requirements=len(all_items),
        done_count=sum(1 for i in all_items if i.status == "done"),
        partial_count=sum(1 for i in all_items if i.status == "partial"),
        missing_count=sum(1 for i in all_items if i.status == "missing"),
        requirements=[
            ComplianceRequirementItem(
                requirement=i.requirement,
                article_reference=i.article_reference,
                status=i.status,
                action_needed=i.action_needed,
            )
            for i in all_items
        ],
    )
