"""
Webhooks API — configure outbound event delivery URLs.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement POST /webhooks — save a new WebhookConfig for the current user.
  - Implement GET /webhooks — list the user's configured webhooks.
  - Implement DELETE /webhooks/{id} — remove a webhook config.
  - Implement webhook delivery: when a Guard block decision is made in
    POST /guard/scan, call `deliver_webhook(db, user_id, event="guard_block", payload={...})`.
    Use `httpx` (already in requirements) to POST the payload to the configured URL.
    Sign the body with HMAC-SHA256 using the stored secret and set the
    X-AegisAI-Signature header.
  - Acceptance criteria: configuring a webhook URL and triggering a guard
    block results in a POST request to that URL within 5 seconds.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.webhook import WebhookCreate, WebhookResponse

router = APIRouter()


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a new webhook endpoint for the current user.

    TODO (help wanted): create a WebhookConfig row and return it.
    """
    # TODO: implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all webhook configs for the current user.

    TODO (help wanted): query WebhookConfig by user_id.
    """
    # TODO: implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a webhook config (must belong to current user).

    TODO (help wanted): fetch by id + user_id, 404 if missing, then delete.
    """
    # TODO: implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )
