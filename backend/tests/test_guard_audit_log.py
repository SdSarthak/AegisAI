import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.guard_audit_log import GuardAuditLog

guard_module = "app.api.v1.guard"


@pytest.fixture(autouse=True)
def mock_session_local(db_session):
    with patch(f"{guard_module}.SessionLocal", return_value=db_session):
        yield


def _build_mock_guard(decision="allow", confidence=0.95):
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": decision,
        "metadata": {
            "decision_reasoning": {"confidence": confidence, "reasoning": "Mock reasoning"},
            "regex_analysis": {"matched_patterns": [], "flag": False, "risk_score": 0.0},
            "intent_analysis": {"intent": "benign", "confidence": 0.98},
        },
    }
    return mock_guard


class TestGuardAuditLogModel:
    def test_create_audit_log(self, db_session: Session):
        user = User(email="audit-test@example.com", hashed_password="pw")
        db_session.add(user)
        db_session.commit()
        log = GuardAuditLog(
            user_id=user.id, prompt_hash="abc123", decision="block",
            threat_type="ml", confidence_score=0.95,
        )
        db_session.add(log)
        db_session.commit()
        saved = db_session.query(GuardAuditLog).first()
        assert saved.user_id == user.id
        assert saved.prompt_hash == "abc123"
        assert saved.decision == "block"
        assert saved.threat_type == "ml"
        assert saved.confidence_score == 0.95
        assert saved.timestamp is not None

    def test_audit_log_default_threat_type(self, db_session: Session):
        user = User(email="audit-default@example.com", hashed_password="pw")
        db_session.add(user)
        db_session.commit()
        log = GuardAuditLog(
            user_id=user.id, prompt_hash="def456", decision="allow", confidence_score=0.5,
        )
        db_session.add(log)
        db_session.commit()
        saved = db_session.query(GuardAuditLog).first()
        assert saved.threat_type == "none"


@pytest.fixture
def shared_ctx(db_engine):
    """Create a shared client+session fixture that tests use."""
    from app.main import app

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    user = User(email="guard-shared@example.com", hashed_password="pw")
    session.add(user)
    session.commit()
    session.refresh(user)

    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    yield client, session, user

    app.dependency_overrides.clear()
    session.close()
    transaction.rollback()
    connection.close()


class TestGuardAuditLogAPI:
    def test_get_audit_log_empty(self, shared_ctx):
        client, _, _ = shared_ctx
        response = client.get("/api/v1/guard/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_audit_log_with_entries(self, shared_ctx):
        client, session, user = shared_ctx
        for i in range(3):
            session.add(GuardAuditLog(
                user_id=user.id, prompt_hash=f"h{i}", decision="allow",
                threat_type="none", confidence_score=0.9,
            ))
        session.commit()
        response = client.get("/api/v1/guard/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_audit_log_scoped_to_user(self, shared_ctx):
        client, session, user = shared_ctx
        other = User(email="other@example.com", hashed_password="pw")
        session.add(other)
        session.commit()
        session.add(GuardAuditLog(user_id=user.id, prompt_hash="mine", decision="allow", confidence_score=0.9))
        session.add(GuardAuditLog(user_id=other.id, prompt_hash="theirs", decision="block", confidence_score=0.95))
        session.commit()
        response = client.get("/api/v1/guard/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["prompt_hash"] == "mine"

    def test_audit_log_filter_by_decision(self, shared_ctx):
        client, session, user = shared_ctx
        session.add(GuardAuditLog(user_id=user.id, prompt_hash="a", decision="allow", confidence_score=0.9))
        session.add(GuardAuditLog(user_id=user.id, prompt_hash="b", decision="block", confidence_score=0.95))
        session.add(GuardAuditLog(user_id=user.id, prompt_hash="c", decision="sanitize", confidence_score=0.8))
        session.commit()
        response = client.get("/api/v1/guard/audit-log?decision=block")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["prompt_hash"] == "b"

    def test_audit_log_pagination(self, shared_ctx):
        client, session, user = shared_ctx
        for i in range(5):
            session.add(GuardAuditLog(
                user_id=user.id, prompt_hash=f"h{i}", decision="allow",
                threat_type="none", confidence_score=0.9,
            ))
        session.commit()
        response = client.get("/api/v1/guard/audit-log?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2

    def test_audit_log_invalid_date_format(self, shared_ctx):
        client, _, _ = shared_ctx
        response = client.get("/api/v1/guard/audit-log?date_from=invalid")
        assert response.status_code == 400

    def test_audit_log_scan_writes_log(self, shared_ctx):
        client, session, user = shared_ctx
        mock_guard = _build_mock_guard("allow", 0.95)
        with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
            response = client.post("/api/v1/guard/scan", json={"prompt": "hello"})
        assert response.status_code == 200
        assert session.query(GuardAuditLog).count() == 1

    def test_audit_log_block_scan_writes_log(self, shared_ctx):
        client, session, user = shared_ctx
        mock_guard = _build_mock_guard("block", 0.99)
        with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
            response = client.post("/api/v1/guard/scan", json={"prompt": "bad"})
        assert response.status_code == 200
        logs = session.query(GuardAuditLog).all()
        assert len(logs) == 1
        assert logs[0].decision == "block"
        assert logs[0].confidence_score == 0.99

    def test_audit_log_bulk_scan_writes_logs(self, shared_ctx):
        client, session, _ = shared_ctx
        mock_guard = _build_mock_guard("allow", 0.9)
        with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
            response = client.post(
                "/api/v1/guard/scan/batch", json={"prompts": ["p1", "p2", "p3"]}
            )
        assert response.status_code == 200
        assert session.query(GuardAuditLog).count() == 3
