"""
Notifications API — in-app event feed for users.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationMarkRead,
    NotificationResponse,
)

router = APIRouter()


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    message: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
):
    """Create and store a notification."""

    notification = Notification(
        user_id=user_id,
        notification_type=type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return notifications for the current user."""

    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = (
        query.order_by(Notification.created_at.desc())
        .all()
    )

    return notifications


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    body: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark notifications as read."""

    notifications = (
        db.query(Notification)
        .filter(
            Notification.id.in_(body.ids),
            Notification.user_id == current_user.id,
        )
        .all()
    )

    for notification in notifications:
        notification.is_read = True

    db.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a notification."""

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    db.delete(notification)
    db.commit()
    