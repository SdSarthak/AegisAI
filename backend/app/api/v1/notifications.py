"""
Notifications API — in-app event feed for users.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement GET /notifications — return paginated list of notifications for
    the current user, newest first. Support ?unread_only=true query param.
  - Implement POST /notifications/read — accept {"ids": [1, 2, 3]} body and
    mark those notifications as read (is_read=True).
  - Implement DELETE /notifications/{id} — delete a single notification
    (must belong to the current user).
  - Add a helper function `create_notification(db, user_id, type, title, message)`
    that other modules can import to emit notifications.
  - Acceptance criteria: after a Guard scan is blocked, a new GUARD_BLOCK
    notification appears in GET /notifications for that user.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationMarkRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return notifications for the current user.

    TODO (help wanted): query the notifications table filtered by user_id,
    optionally filter is_read=False, order by created_at DESC.
    """
    # TODO: implement — replace with real DB query
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    body: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a list of notification IDs as read.

    TODO (help wanted): bulk-update is_read=True for the given IDs,
    ensuring they belong to current_user (prevent IDOR).
    """
    # TODO: implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a single notification.

    TODO (help wanted): fetch by ID + user_id, return 404 if not found, then delete.
    """
    # TODO: implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )
