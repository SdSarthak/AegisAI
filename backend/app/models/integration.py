from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class IntegrationType(str, enum.Enum):
    jira = "jira"
    linear = "linear"


class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    integration_type = Column(Enum(IntegrationType), nullable=False)
    base_url = Column(String(512), nullable=True)   # Jira only
    email = Column(String(255), nullable=True)       # Jira only
    api_token = Column(Text, nullable=False)  # Jira: API token, Linear: API key
    project_key = Column(String(255), nullable=True) # Jira: project key, Linear: team ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="integrations")