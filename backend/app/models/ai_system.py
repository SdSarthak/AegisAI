from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class RiskLevel(str, enum.Enum):
    UNACCEPTABLE = "unacceptable"  # Banned
    HIGH = "high"                   # Strict requirements
    LIMITED = "limited"             # Transparency obligations
    MINIMAL = "minimal"             # No specific requirements


class ComplianceStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"


class AISystem(Base):
    __tablename__ = "ai_systems"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50))
    
    # Classification
    use_case = Column(String(255))  # e.g., "CV Screening", "Candidate Ranking"
    sector = Column(String(255))    # e.g., "HR Tech", "Finance", "Healthcare"
    risk_level = Column(Enum(RiskLevel), nullable=True)
    
    # Compliance tracking
    compliance_status = Column(Enum(ComplianceStatus), default=ComplianceStatus.NOT_STARTED)
    compliance_score = Column(Float, nullable=True, default=None)  # 0.0–100.0, null until classification runs
    
    # Questionnaire responses (JSON)
    questionnaire_responses = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="ai_systems")
    risk_assessments = relationship("RiskAssessment", back_populates="ai_system")
    documents = relationship("Document", back_populates="ai_system")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=False)
    
    # Assessment details
    assessment_type = Column(String(100))  # "initial", "periodic", "incident"
    risk_level = Column(Enum(RiskLevel))
    
    # Findings
    findings = Column(JSON, default=list)  # List of risk findings
    recommendations = Column(JSON, default=list)  # List of recommendations
    
    # Scores
    overall_score = Column(Integer)  # 0-100
    data_governance_score = Column(Integer)
    transparency_score = Column(Integer)
    human_oversight_score = Column(Integer)
    robustness_score = Column(Integer)
    
    # Timestamps
    assessed_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime)
    
    # Relationships
    ai_system = relationship("AISystem", back_populates="risk_assessments")
