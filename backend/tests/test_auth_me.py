import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier


def _build_test_session_local(database_url: str):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_patch_me_updates_profile_fields(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'auth_me.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        full_name="Old Name",
        company_name="Old Company",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "New Name", "company_name": "New Company"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "New Name"
    assert data["company_name"] == "New Company"

    refreshed = db.query(User).filter(User.id == user.id).first()
    assert refreshed.full_name == "New Name"
    assert refreshed.company_name == "New Company"

    app.dependency_overrides.clear()
    db.close()