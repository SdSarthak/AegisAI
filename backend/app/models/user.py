from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    company_name = Column(String(100))

    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    onboarding_completed = Column(Boolean, default=False)
    dashboard_layout = Column(JSON, nullable=True)

    guard_sanitization_level = Column(String(20), nullable=False, default="medium")
    guard_malicious_threshold = Column(Float, nullable=False, default=0.8)
    guard_suspicious_threshold = Column(Float, nullable=False, default=0.5)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ai_systems = relationship("AISystem", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    webhook_configs = relationship("WebhookConfig", back_populates="user")
    notifications = relationship("Notification", back_populates="user")