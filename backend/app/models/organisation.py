"""
Organisation model — multi-tenancy support for AegisAI.

Users belong to an Organisation; AI systems and documents are scoped to orgs.
OrganisationMember is the join table that records per-user roles within an org.

Roles:
    admin  — can update org details, invite/remove members
    member — read-only access to org resources
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class OrgRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)

    # Human-readable name (e.g. "Acme Corp")
    name = Column(String(255), nullable=False)

    # URL-safe unique slug (e.g. "acme-corp"), auto-generated from name if not provided
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # The user who created / owns the org
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_org")
    members = relationship("OrganisationMember", back_populates="organisation", cascade="all, delete-orphan")
    ai_systems = relationship("AISystem", back_populates="organisation")
    documents = relationship("Document", back_populates="organisation")


class OrganisationMember(Base):
    """Join table: which users belong to which org, and their role."""

    __tablename__ = "organisation_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(Enum(OrgRole), nullable=False, default=OrgRole.MEMBER)

    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="members")
    user = relationship("User", back_populates="org_memberships")
