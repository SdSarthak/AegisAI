import pytest
from app.models.notification import Notification
from app.models.user import User

def test_notification_model_exists():
    assert Notification.__tablename__ == "notifications"

def test_user_has_notifications_relationship():
    assert hasattr(User, "notifications")