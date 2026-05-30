from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"  # $99/mo
    GROWTH = "growth"  # $299/mo
    SCALE = "scale"  # $499/mo


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    company_name = Column(String(100))

    # Subscription
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Organisation membership (nullable — users without an org are still valid)
    # use_alter=True defers the FK constraint so create_all() can handle the
    # circular reference: users.org_id → organisations.id ↔ organisations.owner_id → users.id
    org_id = Column(
        Integer,
        ForeignKey("organisations.id", use_alter=True, name="fk_users_org_id"),
        nullable=True,
        index=True,
    )

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    onboarding_completed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ai_systems = relationship("AISystem", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    webhook_configs = relationship("WebhookConfig", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    # Organisation relationships
    owned_org = relationship(
        "Organisation",
        foreign_keys="Organisation.owner_id",
        back_populates="owner",
        uselist=False,
    )
    org_memberships = relationship("OrganisationMember", back_populates="user", cascade="all, delete-orphan")