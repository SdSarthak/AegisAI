"""
Notifications API — in-app event feed for users.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse, NotificationMarkRead
from app.schemas.pagination import PaginatedResponse


router = APIRouter()


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
) -> Notification:
    """Create and persist a new user notification.

    This is an internal helper function, not an API endpoint.

    Args:
        db: SQLAlchemy session.
        user_id: Target user ID to receive the notification.
        notification_type: String identifier (e.g., ``"guard_block"``).
        title: Short title for the notification.
        message: Detailed body text.
        resource_type: Optional related resource (e.g., ``"guard_scan"``).
        resource_id: Optional ID of the related resource.

    Returns:
        Notification: The newly created database record.
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated notifications for the current user.

    Results are sorted newest-first.

    Args:
        unread_only: If ``True``, filters out notifications marked as read.
        page: 1-indexed page number (default 1).
        limit: Items per page (default 50, max 100).
        current_user: Authenticated user (injected via JWT).
        db: SQLAlchemy session (injected).

    Returns:
        PaginatedResponse[NotificationResponse]: The requested notifications.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()

    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=notifications,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    body: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a list of notification IDs as read.

    Performs a bulk update.  Silently ignores IDs that do not exist or
    belong to other users.

    Args:
        body: ``NotificationMarkRead`` schema containing a list of ``ids``.
        current_user: Authenticated user (injected via JWT).
        db: SQLAlchemy session (injected).

    Returns:
        None: On success (HTTP 204).
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.id.in_(body.ids),
    ).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )

    db.commit()
    return None


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single notification owned by the current user.

    Args:
        notification_id: Primary-key of the notification to delete.
        current_user: Authenticated user (injected via JWT).
        db: SQLAlchemy session (injected).

    Returns:
        None: On success (HTTP 204).

    Raises:
        HTTPException(404): If the notification does not exist or does
            not belong to the current user.
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    db.delete(notification)
    db.commit()
    return None
