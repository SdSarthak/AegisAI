"""API for the in-app notification feed and read-state updates."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationMarkRead,
    NotificationResponse,
    NotificationUnreadCount,
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
    """Create and persist a notification for a user."""
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
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's notifications with optional unread filtering."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()

    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=notifications,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
def unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the number of unread notifications for the current user."""
    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )

    return NotificationUnreadCount(unread_count=unread_count)


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    body: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a batch of notifications as read for the current user."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.id.in_(body.ids),
    ).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )

    db.commit()
    return


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications for the current user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )

    db.commit()
    return


@router.delete("/read", status_code=status.HTTP_204_NO_CONTENT)
def delete_read_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all read notifications owned by the current user."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(True),
    ).delete(synchronize_session=False)

    db.commit()
    return


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one notification owned by the current user."""
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
    return
