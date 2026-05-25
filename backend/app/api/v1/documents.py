@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    doc_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new document for the authenticated user.

    Args:
        doc_data (DocumentCreate): Document creation payload.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        DocumentResponse: Newly created document information.
    """

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


@router.get("/", response_model=PaginatedResponse[DocumentResponse])
def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve paginated documents for the authenticated user.

    Args:
        page (int): Current pagination page number.
        limit (int): Maximum number of items per page.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        PaginatedResponse[DocumentResponse]:
        Paginated list of user documents.
    """

    base_query = db.query(Document).filter(
        Document.owner_id == current_user.id
    )

    total = base_query.count()
    offset = (page - 1) * limit

    documents = (
        base_query.offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=documents,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific document owned by the authenticated user.

    Args:
        document_id (int): ID of the document.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        DocumentResponse: Requested document information.

    Raises:
        HTTPException: If the document is not found.
    """

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


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    body: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update document content for the authenticated user.

    Args:
        document_id (int): ID of the document to update.
        body (DocumentUpdateRequest): Updated document content payload.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        DocumentResponse: Updated document information.

    Raises:
        HTTPException: If the document is not found.
    """

    # Fetch document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Update content
    document.content = body.content

    db.commit()
    db.refresh(document)

    return document


@router.post("/generate", response_model=DocumentResponse)
def generate_document(
    request: DocumentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a compliance document for an AI system.

    Args:
        request (DocumentGenerateRequest):
            Document generation request payload.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        DocumentResponse: Generated compliance document.

    Raises:
        HTTPException:
            If the AI system or template is not found.
    """

    # Get the AI system
    ai_system = (
        db.query(AISystem)
        .filter(
            AISystem.id == request.ai_system_id,
            AISystem.owner_id == current_user.id
        )
        .first()
    )

    if not ai_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )

    # Get template
    template = DOCUMENT_TEMPLATES.get(request.document_type)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No template available for {request.document_type}",
        )

    # Get latest risk assessment if available
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
            company_name=current_user.company_name
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)

        logger.warning(
            f"LLM generation failed, falling back to template: {str(e)}"
        )

        from datetime import datetime

        content = template.format(
            system_name=ai_system.name,
            version=ai_system.version or "1.0",
            use_case=ai_system.use_case or "Not specified",
            sector=ai_system.sector or "Not specified",
            description=ai_system.description or "No description provided",
            risk_level=(
                ai_system.risk_level.value
                if ai_system.risk_level
                else "Not assessed"
            ),
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            company_name=current_user.company_name or "Not specified",
            classification_reasons="See risk assessment details",
            recommendations="Based on risk assessment",
            requirements="See applicable requirements above",
            next_steps="Complete all checklist items"
        )

    # Create document
    document = Document(
        owner_id=current_user.id,
        ai_system_id=ai_system.id,
        title=(
            f"{request.document_type.value.replace('_', ' ').title()} "
            f"- {ai_system.name}"
        ),
        document_type=request.document_type,
        status=DocumentStatus.GENERATED,
        content=content,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document owned by the authenticated user.

    Args:
        document_id (int): ID of the document to delete.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        None: Empty response with HTTP 204 status code.

    Raises:
        HTTPException: If the document is not found.
    """

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


@router.get("/{document_id}/pdf")
def export_document_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a document as a PDF file.

    Args:
        document_id (int): ID of the document to export.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        StreamingResponse:
        PDF file response for document download.

    Raises:
        HTTPException:
            If the document is not found,
            has no content,
            or PDF generation fails.
    """

    # Retrieve the document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content to export"
        )

    # Generate PDF
    pdf_buffer = BytesIO()