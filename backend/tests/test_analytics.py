import sys
from unittest.mock import MagicMock

# Mock out heavy ML libraries to bypass ModuleNotFoundError on Python 3.8.10
for module_name in [
    "torch", "transformers", "sklearn", "sklearn.feature_extraction", 
    "sklearn.feature_extraction.text", "sklearn.linear_model", 
    "pandas", "numpy", "datasets", "mlflow", "faiss", "pdfplumber", "pypdf",
    "reportlab", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
    "reportlab.lib", "reportlab.lib.pagesizes", "reportlab.platypus",
    "langchain", "langchain.chains", "langchain.document_loaders", 
    "langchain.text_splitter", "langchain.embeddings", "langchain.vectorstores",
    "langchain_community", "langchain_community.vectorstores", 
    "langchain_community.embeddings", "langchain_community.document_loaders",
    "langchain_openai"
]:
    sys.modules[module_name] = MagicMock()

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus


def _build_test_session_local(database_url: str):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_analytics_summary_calculates_correct_metrics(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'analytics_test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    
    # 1. Create a primary user and a secondary user (to verify isolation)
    user1 = User(
        email="owner@example.com",
        hashed_password="hashed",
        full_name="Owner User",
        is_active=True,
        is_verified=True,
    )
    user2 = User(
        email="other@example.com",
        hashed_password="hashed",
        full_name="Other User",
        is_active=True,
        is_verified=True,
    )
    db.add(user1)
    db.add(user2)
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # 2. Add AI Systems for user1
    sys1 = AISystem(
        owner_id=user1.id,
        name="System 1",
        risk_level=RiskLevel.HIGH,
        compliance_status=ComplianceStatus.COMPLIANT,
        compliance_score=80.0,
    )
    sys2 = AISystem(
        owner_id=user1.id,
        name="System 2",
        risk_level=RiskLevel.MINIMAL,
        compliance_status=ComplianceStatus.COMPLIANT,
        compliance_score=90.0,
    )
    sys3 = AISystem(
        owner_id=user1.id,
        name="System 3",
        risk_level=RiskLevel.LIMITED,
        compliance_status=ComplianceStatus.IN_PROGRESS,
        compliance_score=None,  # Should be ignored in average score calculations
    )
    sys4 = AISystem(
        owner_id=user1.id,
        name="System 4",
        risk_level=RiskLevel.UNACCEPTABLE,
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        compliance_score=40.0,
    )
    
    # AI System for user2 (should NOT affect user1's analytics stats)
    sys_other = AISystem(
        owner_id=user2.id,
        name="Other User's System",
        risk_level=RiskLevel.HIGH,
        compliance_status=ComplianceStatus.COMPLIANT,
        compliance_score=100.0,
    )

    db.add_all([sys1, sys2, sys3, sys4, sys_other])
    db.commit()

    # 3. Setup overrides
    def override_current_user():
        return user1

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.get("/api/v1/analytics/summary")

    # 4. Assert response is successful and contains correct figures
    assert response.status_code == 200
    data = response.json()

    assert data["total_systems"] == 4
    # (80.0 + 90.0 + 40.0) / 3 = 70.0
    assert data["avg_compliance_score"] == 70.0
    assert data["compliant_count"] == 2
    assert data["high_risk_count"] == 1

    # Map distribution list to a dict for easy assertion
    dist_map = {item["name"]: item["value"] for item in data["risk_distribution"]}
    
    assert dist_map["Minimal Risk"] == 1
    assert dist_map["Limited Risk"] == 1
    assert dist_map["High Risk"] == 1
    assert dist_map["Unacceptable Risk"] == 1

    # Cleanup overrides
    app.dependency_overrides.clear()
    db.close()
