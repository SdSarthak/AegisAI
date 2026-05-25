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
from app.schemas.notification import (
    NotificationResponse,
    NotificationMarkRead,
)
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
    """
    Create and store a new notification for a user.

    Args:
        db (Session): Database session dependency.
        user_id (int): ID of the notification recipient.
        notification_type (str): Type/category of notification.
        title (str): Notification title.
        message (str): Notification message content.
        resource_type (str | None): Associated resource type.
        resource_id (int | None): Associated resource ID.

    Returns:
        Notification: Newly created notification object.
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
    """
    Retrieve notifications for the authenticated user.

    Args:
        unread_only (bool): Whether to return only unread notifications.
        page (int): Current pagination page number.
        limit (int): Maximum number of notifications per page.
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        PaginatedResponse[NotificationResponse]:
        Paginated list of user notifications.
    """

    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )

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
    """
    Mark selected notifications as read.

    Args:
        body (NotificationMarkRead): Notification IDs to mark as read.
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        None: Empty response with HTTP 204 status code.
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
    """
    Delete a notification owned by the authenticated user.

    Args:
        notification_id (int): ID of the notification to delete.
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        None: Empty response with HTTP 204 status code.

    Raises:
        HTTPException: If the notification does not exist.
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