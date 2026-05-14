from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
import re
from xml.sax.saxutils import escape

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.ai_system import AISystem
from app.models.document import Document, DocumentType, DocumentStatus
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentGenerateRequest,
    DocumentUpdateRequest,
)
from app.schemas.pagination import PaginatedResponse
from app.services.llm import generate_compliance_narrative

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER

router = APIRouter()


DOCUMENT_TEMPLATES = {
    DocumentType.TECHNICAL_DOCUMENTATION: """...""",
    DocumentType.RISK_ASSESSMENT: """...""",
    DocumentType.CONFORMITY_DECLARATION: """...""",
}


# ---------------- CREATE ----------------
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    doc_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    document = Document(
        owner_id=current_user.id,
        title=doc_data.title,
        document_type=doc_data.document_type,
        ai_system_id=doc_data.ai_system_id,
        content=doc_data.content,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


# ---------------- LIST ----------------
@router.get("/", response_model=PaginatedResponse[DocumentResponse])
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)
    ),
):
    base_query = db.query(Document).filter(Document.owner_id == current_user.id)
    total = base_query.count()
    offset = (page - 1) * limit

    documents = base_query.offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=documents,
        total=total,
        page=page,
        limit=limit,
    )


# ---------------- GET ----------------
@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)
    ),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


# ---------------- UPDATE ----------------
@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    body: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)
    ),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document.content = body.content
    db.commit()
    db.refresh(document)

    return document


# ---------------- GENERATE ----------------
@router.post("/generate", response_model=DocumentResponse)
def generate_document(
    request: DocumentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ANALYST, UserRole.ADMIN)
    ),
):
    ai_system = (
        db.query(AISystem)
        .filter(
            AISystem.id == request.ai_system_id,
            AISystem.owner_id == current_user.id,
        )
        .first()
    )

    if not ai_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    template = DOCUMENT_TEMPLATES.get(request.document_type)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No template available",
        )

    from app.models.ai_system import RiskAssessment

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.ai_system_id == ai_system.id)
        .order_by(RiskAssessment.assessed_at.desc())
        .first()
    )

    try:
        content = generate_compliance_narrative(
            document_type=request.document_type,
            ai_system=ai_system,
            risk_assessment=assessment,
            company_name=current_user.company_name,
        )
    except Exception:
        from datetime import datetime

        content = template.format(
            system_name=ai_system.name,
            version=ai_system.version or "1.0",
            use_case=ai_system.use_case or "Not specified",
            sector=ai_system.sector or "Not specified",
            description=ai_system.description or "No description",
            risk_level=ai_system.risk_level.value if ai_system.risk_level else "N/A",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            company_name=current_user.company_name or "",
            classification_reasons="N/A",
            recommendations="N/A",
            requirements="N/A",
            next_steps="N/A",
        )

    document = Document(
        owner_id=current_user.id,
        ai_system_id=ai_system.id,
        title=f"{request.document_type.value} - {ai_system.name}",
        document_type=request.document_type,
        status=DocumentStatus.GENERATED,
        content=content,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


# ---------------- DELETE ----------------
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    db.delete(document)
    db.commit()


# ---------------- PDF EXPORT ----------------
@router.get("/{document_id}/pdf")
def export_document_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)
    ),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.content:
        raise HTTPException(status_code=400, detail="No content")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
    )

    body_style = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
    )

    story.append(Paragraph(document.title, title_style))
    story.append(Spacer(1, 0.2 * inch))

    for raw_line in document.content.split("\n"):
        line = escape(raw_line.strip())

        if not raw_line.strip():
            story.append(Spacer(1, 0.1 * inch))

        elif raw_line.startswith("# "):
            story.append(Paragraph(escape(raw_line[2:]), styles["Heading1"]))

        elif raw_line.startswith("## "):
            story.append(Paragraph(escape(raw_line[3:]), styles["Heading2"]))

        elif raw_line.startswith("- "):
            story.append(Paragraph("• " + escape(raw_line[2:]), body_style))

        else:
            story.append(Paragraph(line, body_style))

    doc.build(story)

    pdf = buffer.getvalue()

    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document.title}.pdf"'
        },
    )