import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.api.v1.guard import user_guard_configs
from app.modules.guard.pii_masking import PIIMaskingFilter
from app.modules.guard.hallucination import HallucinationValidator


@pytest.fixture(autouse=True)
def clear_in_memory_config():
    user_guard_configs.clear()
    yield
    user_guard_configs.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(email="middleware-test@example.com", hashed_password="hashedpassword")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.expunge(user)
    return user


@pytest.fixture
def authenticated_client(client: TestClient, test_user: User):
    def override_current_user():
        from app.core.context import user_id_ctx
        user_id_ctx.set(test_user.id)
        return test_user

    from app.main import app
    app.dependency_overrides[get_current_user] = override_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_pii_masking_filter_emails():
    filter_obj = PIIMaskingFilter()
    text = "Send an email to alex.jones@example.org or support@google.com."
    masked = filter_obj.mask(text)
    assert "[EMAIL_MASKED]" in masked
    assert "alex.jones@example.org" not in masked
    assert "support@google.com" not in masked


def test_pii_masking_filter_phones():
    filter_obj = PIIMaskingFilter()
    # No context word => should not mask to prevent false positives
    text_no_context = "My code is +1-555-019-2834."
    assert filter_obj.mask(text_no_context) == text_no_context

    # With context word => should mask
    text_context = "Please call me at +1-555-019-2834."
    masked = filter_obj.mask(text_context)
    assert "[PHONE_MASKED]" in masked
    assert "+1-555-019-2834" not in masked


def test_pii_masking_filter_api_keys():
    filter_obj = PIIMaskingFilter()
    # Mocking Google API key
    text = "Your API Key is AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
    masked = filter_obj.mask(text)
    assert "[API_KEY_MASKED]" in masked
    assert "AIzaSy" not in masked

    # Generic secret assignment
    text_assign = "api_key = \"mysecretkey1234567\""
    masked_assign = filter_obj.mask(text_assign)
    assert "[API_KEY_MASKED]" in masked_assign
    assert "mysecretkey1234567" not in masked_assign


def test_hallucination_validator():
    validator = HallucinationValidator()
    mock_result = MagicMock()
    mock_result.score = 0.85
    mock_result.confidence = "HIGH"

    with patch.object(validator.checker, "check", return_value=mock_result) as mock_check:
        score = validator.check("This is a grounded answer.", ["This is source context chunk."])
        assert score == 0.85
        mock_check.assert_called_once_with(
            answer="This is a grounded answer.",
            chunks=["This is source context chunk."]
        )


def test_middleware_pii_masking_non_streaming(authenticated_client: TestClient, test_user: User):
    # Enable PII masking in configuration
    user_guard_configs[test_user.id] = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
        "pii_masking_enabled": True,
        "hallucination_threshold": 0.5,
    }

    mock_rag_response = {
        "answer": "You can reach us at contact@example.com or call 555-123-4567.",
        "sources": [],
        "answer_id": "dummy_id",
        "grounding_score": 0.9,
        "grounding_confidence": "HIGH",
        "guard_triggered": False,
        "guard_decision": "ALLOW",
        "chunks_total": 1,
        "chunks_dropped": 0,
        "warning": None,
    }

    from app.main import app
    from app.api.v1.rag import guard_rag_question, GuardedRAGQuestion

    def mock_guard_rag_question():
        return GuardedRAGQuestion(
            question="What is contact info?",
            original_question="What is contact info?",
            guard_triggered=False,
            guard_decision="ALLOW",
        )

    app.dependency_overrides[guard_rag_question] = mock_guard_rag_question

    try:
        # Intercept RAG endpoint return values
        with patch("app.api.v1.rag.get_qa_chain") as mock_chain:
            mock_qa = MagicMock()
            mock_qa.return_value = {
                "result": "You can reach us at contact@example.com or call 555-123-4567.",
                "source_documents": [MagicMock(page_content="contact us phone")],
                "chunks_total": 1,
                "chunks_dropped": 0,
                "grounding_score": 0.9,
                "grounding_confidence": "HIGH",
                "warning": None,
            }
            mock_chain.return_value = mock_qa

            response = authenticated_client.post("/api/v1/rag/query", json={"question": "What is contact info?"})
    finally:
        app.dependency_overrides.pop(guard_rag_question, None)

    assert response.status_code == 200
    data = response.json()
    assert "[EMAIL_MASKED]" in data["answer"]
    assert "[PHONE_MASKED]" in data["answer"]
    assert "contact@example.com" not in data["answer"]


def test_middleware_hallucination_blocking_non_streaming(authenticated_client: TestClient, test_user: User):
    # Configure strict hallucination threshold (0.8)
    user_guard_configs[test_user.id] = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
        "pii_masking_enabled": False,
        "hallucination_threshold": 0.8,
    }

    from app.main import app
    from app.api.v1.rag import guard_rag_question, GuardedRAGQuestion

    def mock_guard_rag_question():
        return GuardedRAGQuestion(
            question="What is the capital?",
            original_question="What is the capital?",
            guard_triggered=False,
            guard_decision="ALLOW",
        )

    app.dependency_overrides[guard_rag_question] = mock_guard_rag_question

    try:
        # Response has low grounding score (0.4)
        with patch("app.api.v1.rag.get_qa_chain") as mock_chain:
            mock_qa = MagicMock()
            mock_qa.return_value = {
                "result": "Some ungrounded hallucinated claim.",
                "source_documents": [MagicMock(page_content="sources context")],
                "chunks_total": 1,
                "chunks_dropped": 0,
                "grounding_score": 0.4,
                "grounding_confidence": "LOW",
                "warning": "Low grounding",
            }
            mock_chain.return_value = mock_qa

            response = authenticated_client.post("/api/v1/rag/query", json={"question": "What is the capital?"})
    finally:
        app.dependency_overrides.pop(guard_rag_question, None)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "hallucination_detected"
    assert "blocked due to high likelihood of hallucination" in data["detail"]["safe_message"]


def test_middleware_pii_masking_streaming(authenticated_client: TestClient, test_user: User):
    # Enable PII masking in configuration
    user_guard_configs[test_user.id] = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
        "pii_masking_enabled": True,
        "hallucination_threshold": 0.3,
    }

    async def mock_stream_generator(*args, **kwargs):
        yield "event: meta\ndata: {\"answer_id\": \"1\", \"citations\": []}\n\n"
        yield "event: token\ndata: {\"delta\": \"My email is \"}\n\n"
        yield "event: token\ndata: {\"delta\": \"support@\"}\n\n"
        yield "event: token\ndata: {\"delta\": \"google.com \"}\n\n"
        yield "event: token\ndata: {\"delta\": \"for help.\"}\n\n"
        yield "event: done\ndata: {\"finish_reason\": \"stop\", \"duration_ms\": 100, \"grounding_score\": 0.9}\n\n"

    with patch("app.api.v1.rag.load_vector_store"), \
         patch("app.api.v1.rag.stream_rag_answer", side_effect=mock_stream_generator):
        response = authenticated_client.post("/api/v1/rag/query/stream", json={"question": "Who are you?"})

    assert response.status_code == 200
    content = response.text
    assert "[EMAIL_MASKED]" in content
    assert "support@google.com" not in content


def test_middleware_hallucination_blocking_streaming(authenticated_client: TestClient, test_user: User):
    # Configure hallucination blocker
    user_guard_configs[test_user.id] = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
        "pii_masking_enabled": False,
        "hallucination_threshold": 0.7,
    }

    async def mock_stream_generator(*args, **kwargs):
        yield "event: meta\ndata: {\"answer_id\": \"1\", \"citations\": []}\n\n"
        yield "event: token\ndata: {\"delta\": \"Hallucinated output token\"}\n\n"
        # done event contains grounding score 0.4, which is below threshold 0.7
        yield "event: done\ndata: {\"finish_reason\": \"stop\", \"duration_ms\": 100, \"grounding_score\": 0.4}\n\n"

    with patch("app.api.v1.rag.load_vector_store"), \
         patch("app.api.v1.rag.stream_rag_answer", side_effect=mock_stream_generator):
        response = authenticated_client.post("/api/v1/rag/query/stream", json={"question": "Who are you?"})

    assert response.status_code == 200
    content = response.text
    # Verify the done event is replaced by the error event
    assert "event: error" in content
    assert "hallucination_detected" in content
    assert "event: done" not in content
