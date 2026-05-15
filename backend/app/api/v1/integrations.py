"""Integrations API — Jira and Linear configuration and management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.integration import IntegrationSettings, IntegrationType, IntegrationTicket
from app.schemas.integration import (
    IntegrationSettingsCreate,
    IntegrationSettingsResponse,
    IntegrationTestResponse,
    IntegrationTicketResponse,
)
from app.modules.integrations import JiraClient, LinearClient

router = APIRouter()


def get_client(integration: IntegrationSettings):
    """Get the appropriate client based on integration type."""
    if integration.integration_type == IntegrationType.JIRA:
        return JiraClient(integration.base_url, integration.api_key, integration.username or "")
    elif integration.integration_type == IntegrationType.LINEAR:
        return LinearClient(integration.api_key)
    else:
        raise ValueError(f"Unknown integration type: {integration.integration_type}")


@router.post("/jira", response_model=IntegrationSettingsResponse, status_code=status.HTTP_201_CREATED)
def create_jira_integration(
    payload: IntegrationSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update Jira integration for the current user."""
    if payload.integration_type != IntegrationType.JIRA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected Jira integration type",
        )

    # Check if Jira integration already exists
    existing = db.query(IntegrationSettings).filter(
        IntegrationSettings.user_id == current_user.id,
        IntegrationSettings.integration_type == IntegrationType.JIRA,
    ).first()

    if existing:
        # Update existing
        existing.base_url = payload.base_url
        existing.api_key = payload.api_key.get_secret_value()
        existing.username = payload.username
        existing.project_key = payload.project_key
        existing.create_on_high = payload.create_on_high
        existing.create_on_unacceptable = payload.create_on_unacceptable
        existing.create_gap_tickets = payload.create_gap_tickets
        if payload.gap_ticket_template:
            existing.gap_ticket_template = payload.gap_ticket_template
        integration = existing
    else:
        # Create new
        integration = IntegrationSettings(
            user_id=current_user.id,
            integration_type=IntegrationType.JIRA,
            base_url=payload.base_url,
            api_key=payload.api_key.get_secret_value(),
            username=payload.username,
            project_key=payload.project_key,
            create_on_high=payload.create_on_high,
            create_on_unacceptable=payload.create_on_unacceptable,
            create_gap_tickets=payload.create_gap_tickets,
            gap_ticket_template=payload.gap_ticket_template or {},
        )
        db.add(integration)

    db.commit()
    db.refresh(integration)
    return integration


@router.post("/linear", response_model=IntegrationSettingsResponse, status_code=status.HTTP_201_CREATED)
def create_linear_integration(
    payload: IntegrationSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update Linear integration for the current user."""
    if payload.integration_type != IntegrationType.LINEAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected Linear integration type",
        )

    # Check if Linear integration already exists
    existing = db.query(IntegrationSettings).filter(
        IntegrationSettings.user_id == current_user.id,
        IntegrationSettings.integration_type == IntegrationType.LINEAR,
    ).first()

    if existing:
        # Update existing
        existing.base_url = payload.base_url
        existing.api_key = payload.api_key.get_secret_value()
        existing.team_id = payload.team_id
        existing.create_on_high = payload.create_on_high
        existing.create_on_unacceptable = payload.create_on_unacceptable
        existing.create_gap_tickets = payload.create_gap_tickets
        if payload.gap_ticket_template:
            existing.gap_ticket_template = payload.gap_ticket_template
        integration = existing
    else:
        # Create new
        integration = IntegrationSettings(
            user_id=current_user.id,
            integration_type=IntegrationType.LINEAR,
            base_url=payload.base_url,
            api_key=payload.api_key.get_secret_value(),
            team_id=payload.team_id,
            create_on_high=payload.create_on_high,
            create_on_unacceptable=payload.create_on_unacceptable,
            create_gap_tickets=payload.create_gap_tickets,
            gap_ticket_template=payload.gap_ticket_template or {},
        )
        db.add(integration)

    db.commit()
    db.refresh(integration)
    return integration


@router.get("", response_model=List[IntegrationSettingsResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all integrations for the current user."""
    integrations = db.query(IntegrationSettings).filter(
        IntegrationSettings.user_id == current_user.id
    ).all()
    return integrations


@router.get("/{integration_id}", response_model=IntegrationSettingsResponse)
def get_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific integration."""
    integration = db.query(IntegrationSettings).filter(
        IntegrationSettings.id == integration_id,
        IntegrationSettings.user_id == current_user.id,
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    return integration


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
def test_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test connection to an integration."""
    integration = db.query(IntegrationSettings).filter(
        IntegrationSettings.id == integration_id,
        IntegrationSettings.user_id == current_user.id,
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    try:
        client = get_client(integration)
        result = client.test_connection()
        
        # Update test result in DB
        integration.last_tested_at = datetime.utcnow()
        integration.test_result = result.get("message", "")
        db.commit()

        return IntegrationTestResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            details=result.get("details"),
        )
    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            message=str(e),
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an integration."""
    integration = db.query(IntegrationSettings).filter(
        IntegrationSettings.id == integration_id,
        IntegrationSettings.user_id == current_user.id,
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    db.delete(integration)
    db.commit()


@router.get("/{integration_id}/tickets", response_model=List[IntegrationTicketResponse])
def list_created_tickets(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tickets created by an integration."""
    integration = db.query(IntegrationSettings).filter(
        IntegrationSettings.id == integration_id,
        IntegrationSettings.user_id == current_user.id,
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    tickets = db.query(IntegrationTicket).filter(
        IntegrationTicket.integration_id == integration_id
    ).all()
    return tickets
