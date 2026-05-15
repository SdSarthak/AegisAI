"""Integration settings for Jira and Linear — per user."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class IntegrationType(str, enum.Enum):
    JIRA = "jira"
    LINEAR = "linear"


class IntegrationSettings(Base):
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Integration type
    integration_type = Column(Enum(IntegrationType), nullable=False)

    # Credentials and config
    base_url = Column(String(500), nullable=False)  # e.g., https://jira.company.com or https://api.linear.app
    api_key = Column(String(500), nullable=False)  # API token or personal access token
    username = Column(String(255), nullable=True)  # For Jira: email; for Linear: optional

    # Configuration
    project_key = Column(String(100), nullable=True)  # For Jira: project key (e.g., "PROJ")
    team_id = Column(String(100), nullable=True)  # For Linear: team ID
    create_on_high = Column(Boolean, default=True)  # Create task when system is HIGH risk
    create_on_unacceptable = Column(Boolean, default=True)  # Create task when system is UNACCEPTABLE
    create_gap_tickets = Column(Boolean, default=False)  # Create separate ticket per compliance gap

    # Gap mapping (JSON: gap_type -> issue_type mapping)
    gap_ticket_template = Column(JSON, default=dict)  # e.g., {"explainability": "Task", "oversight": "Bug"}

    # Testing
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime, nullable=True)
    test_result = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="integrations")
    tickets = relationship("IntegrationTicket", back_populates="integration")


class IntegrationTicket(Base):
    """Track created tickets linked to compliance gaps or classifications."""

    __tablename__ = "integration_tickets"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integration_settings.id"), nullable=False)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=False)

    # Ticket info
    external_ticket_id = Column(String(255), nullable=False)  # Jira issue key or Linear issue ID
    external_url = Column(String(500), nullable=True)
    ticket_type = Column(String(100))  # "Task", "Bug", "Story", etc.

    # Link reason
    link_reason = Column(String(100))  # "classification_high", "classification_unacceptable", "gap_{gap_type}"
    gap_type = Column(String(100), nullable=True)  # e.g., "explainability", "oversight"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    integration = relationship("IntegrationSettings", back_populates="tickets")
