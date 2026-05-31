from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.encryption import encrypt
from app.models.user import User
from app.models.integration import UserIntegration, IntegrationType
from app.schemas.integration import JiraIntegrationCreate, LinearIntegrationCreate, IntegrationResponse

router = APIRouter()


@router.post("/jira", response_model=IntegrationResponse)
def save_jira_integration(
    data: JiraIntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(UserIntegration).filter_by(
        user_id=current_user.id, integration_type=IntegrationType.jira
    ).first()

    if existing:
        existing.base_url = data.base_url
        existing.email = data.email
        existing.api_token = encrypt(data.api_token)
        existing.project_key = data.project_key
    else:
        existing = UserIntegration(
            user_id=current_user.id,
            integration_type=IntegrationType.jira,
            base_url=data.base_url,
            email=data.email,
            api_token=encrypt(data.api_token),
            project_key=data.project_key,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


@router.post("/linear", response_model=IntegrationResponse)
def save_linear_integration(
    data: LinearIntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(UserIntegration).filter_by(
        user_id=current_user.id, integration_type=IntegrationType.linear
    ).first()

    if existing:
        existing.api_token = encrypt(data.api_key)
        existing.project_key = data.team_id
    else:
        existing = UserIntegration(
            user_id=current_user.id,
            integration_type=IntegrationType.linear,
            api_token=encrypt(data.api_key),
            project_key=data.team_id,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


@router.get("/", response_model=List[IntegrationResponse])
def get_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(UserIntegration).filter_by(user_id=current_user.id).all()