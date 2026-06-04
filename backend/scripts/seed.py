# backend/scripts/seed.py  #69
"""Database seed script for local development — #69.

Populates a fresh DB with:
  - 1 demo user (admin@aegisai.dev / password123)
  - 3 AI systems at different risk levels
  - 2 risk assessments
  - 3 compliance documents
"""

from datetime import datetime, timedelta

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.core.database import SessionLocal
from app.models.user import User, SubscriptionTier
from app.models.ai_system import (
    AISystem,
    RiskAssessment,
    RiskLevel,
    ComplianceStatus,
)
from app.models.document import (
    Document,
    DocumentType,
    DocumentStatus,
)


def seed_database():  #69
    from app.core.database import engine, Base
    import app.models  # ensure all ORM models are imported
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # ---------------------------------------------------
        # Create Demo User  #69
        # ---------------------------------------------------
        existing_user = (
            db.query(User)
            .filter(User.email == "admin@aegisai.dev")
            .first()
        )

        if existing_user:
            print("Demo user already exists.")
            return

        demo_user = User(  #69
            email="admin@aegisai.dev",
            hashed_password=get_password_hash("password123"),
            full_name="AegisAI Admin",
            company_name="AegisAI Demo",
            subscription_tier=SubscriptionTier.SCALE,
            is_active=True,
            is_verified=True,
        )

        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        print("Demo user created.")

        # ---------------------------------------------------
        # Create AI Systems  #69
        # ---------------------------------------------------
        ai_system_1 = AISystem(  #69
            owner_id=demo_user.id,
            name="CV Screening Assistant",
            description="AI system used for candidate screening.",
            version="1.0",
            use_case="CV Screening",
            sector="HR Tech",
            risk_level=RiskLevel.HIGH,
            compliance_status=ComplianceStatus.IN_PROGRESS,
            compliance_score=78,
            questionnaire_responses={
                "handles_personal_data": True,
                "human_oversight": True,
            },
        )

        ai_system_2 = AISystem(  #69
            owner_id=demo_user.id,
            name="Medical Diagnosis Support",
            description="AI-assisted healthcare diagnosis support.",
            version="2.1",
            use_case="Medical Diagnosis",
            sector="Healthcare",
            risk_level=RiskLevel.HIGH,
            compliance_status=ComplianceStatus.UNDER_REVIEW,
            compliance_score=85,
            questionnaire_responses={
                "critical_decision_support": True,
                "risk_mitigation": True,
            },
        )

        ai_system_3 = AISystem(  #69
            owner_id=demo_user.id,
            name="Customer Support Chatbot",
            description="Minimal-risk customer support chatbot.",
            version="1.5",
            use_case="Customer Support",
            sector="Retail",
            risk_level=RiskLevel.MINIMAL,
            compliance_status=ComplianceStatus.COMPLIANT,
            compliance_score=95,
            questionnaire_responses={
                "uses_llm": True,
                "stores_conversations": False,
            },
        )

        db.add_all([
            ai_system_1,
            ai_system_2,
            ai_system_3,
        ])

        db.commit()

        db.refresh(ai_system_1)
        db.refresh(ai_system_2)
        db.refresh(ai_system_3)

        print("AI systems created.")

        # ---------------------------------------------------
        # Create Risk Assessments  #69
        # ---------------------------------------------------
        assessment_1 = RiskAssessment(  #69
            ai_system_id=ai_system_1.id,
            assessment_type="initial",
            risk_level=RiskLevel.HIGH,
            findings=[
                "Potential bias in hiring recommendations",
                "Insufficient transparency in scoring",
            ],
            recommendations=[
                "Add explainability reports",
                "Increase human review coverage",
            ],
            overall_score=76,
            data_governance_score=80,
            transparency_score=70,
            human_oversight_score=75,
            robustness_score=79,
            assessed_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=180),
        )

        assessment_2 = RiskAssessment(  #69
            ai_system_id=ai_system_2.id,
            assessment_type="periodic",
            risk_level=RiskLevel.HIGH,
            findings=[
                "Healthcare decision support requires stronger validation",
            ],
            recommendations=[
                "Perform additional clinical testing",
                "Improve monitoring pipelines",
            ],
            overall_score=84,
            data_governance_score=88,
            transparency_score=82,
            human_oversight_score=85,
            robustness_score=81,
            assessed_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=365),
        )

        db.add_all([
            assessment_1,
            assessment_2,
        ])

        db.commit()

        print("Risk assessments created.")

        # ---------------------------------------------------
        # Create Compliance Documents  #69
        # ---------------------------------------------------
        document_1 = Document(  #69
            owner_id=demo_user.id,
            ai_system_id=ai_system_1.id,
            title="CV Screening Risk Assessment",
            document_type=DocumentType.RISK_ASSESSMENT,
            status=DocumentStatus.APPROVED,
            content="Detailed risk assessment for CV Screening Assistant.",
            version="1.0",
        )

        document_2 = Document(  #69
            owner_id=demo_user.id,
            ai_system_id=ai_system_2.id,
            title="Healthcare Transparency Notice",
            document_type=DocumentType.TRANSPARENCY_NOTICE,
            status=DocumentStatus.REVIEWED,
            content="Transparency notice for medical AI support system.",
            version="1.2",
        )

        document_3 = Document(  #69
            owner_id=demo_user.id,
            ai_system_id=ai_system_3.id,
            title="Customer Support Technical Documentation",
            document_type=DocumentType.TECHNICAL_DOCUMENTATION,
            status=DocumentStatus.GENERATED,
            content="Technical documentation for chatbot deployment.",
            version="2.0",
        )

        db.add_all([
            document_1,
            document_2,
            document_3,
        ])

        db.commit()

        print("Compliance documents created.")
        print("Database seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error while seeding database: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
