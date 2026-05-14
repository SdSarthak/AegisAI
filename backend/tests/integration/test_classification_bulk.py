import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.ai_system import AISystem


def _authenticate_test_user(db_session):
    user = User(
        email="bulk-test@example.com",
        hashed_password="fakehashedpassword"
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}, user


def test_bulk_classify_returns_partial_results(client, db_session):
    headers, user = _authenticate_test_user(db_session)

    system = AISystem(
        owner_id=user.id,
        name="HR Screening AI",
        questionnaire_responses={
            "use_case_category": "hr_recruitment",
            "is_safety_component": False,
            "affects_fundamental_rights": False,
            "uses_biometric_data": False,
            "makes_automated_decisions": True,
            "hr_recruitment_screening": True,
            "hr_promotion_termination": False,
            "credit_worthiness": False,
            "insurance_risk_assessment": False,
            "law_enforcement": False,
            "border_control": False,
            "justice_system": False,
            "interacts_with_humans": False,
            "generates_synthetic_content": False,
            "emotion_recognition": False,
            "biometric_categorization": False,
        },
    )
    db_session.add(system)
    db_session.commit()

    response = client.post(
        "/api/v1/classification/bulk",
        json={"system_ids": [system.id, 999999]},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert len(payload["results"]) == 2

    success_result = next(r for r in payload["results"] if r["system_id"] == system.id)
    assert success_result["error"] is None
    assert success_result["classification"]["risk_level"] == "high"
    assert "reasons" in success_result["classification"]

    failure_result = next(r for r in payload["results"] if r["system_id"] == 999999)
    assert failure_result["classification"] is None
    assert failure_result["error"] == "AI system not found"

    db_session.refresh(system)
    assert system.risk_level == "high"
