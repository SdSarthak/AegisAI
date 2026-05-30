"""
Organisations API — multi-tenancy endpoints for AegisAI.

Endpoints:
    POST   /api/v1/orgs                              — Create a new org (caller becomes admin)
    GET    /api/v1/orgs/{org_id}                     — Get org details (members only)
    PATCH  /api/v1/orgs/{org_id}                     — Update org name/slug (admin only)
    GET    /api/v1/orgs/{org_id}/members             — List org members (members only)
    POST   /api/v1/orgs/{org_id}/members             — Invite user by email (admin only)
    DELETE /api/v1/orgs/{org_id}/members/{user_id}   — Remove a member (admin only)
"""

import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.organisation import Organisation, OrganisationMember, OrgRole
from app.models.user import User
from app.schemas.organisation import (
    OrgCreate,
    OrgMemberListResponse,
    OrgMemberResponse,
    OrgResponse,
    OrgUpdate,
    InviteMemberRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert a display name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _get_org_or_404(org_id: int, db: Session) -> Organisation:
    """Fetch an org by ID or raise 404."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org


def _get_membership(org_id: int, user_id: int, db: Session) -> OrganisationMember | None:
    """Return the membership record or None."""
    return (
        db.query(OrganisationMember)
        .filter(OrganisationMember.org_id == org_id, OrganisationMember.user_id == user_id)
        .first()
    )


def _require_member(org_id: int, current_user: User, db: Session) -> OrganisationMember:
    """Dependency helper — user must be a member of the org."""
    membership = _get_membership(org_id, current_user.id, db)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organisation",
        )
    return membership


def _require_admin(org_id: int, current_user: User, db: Session) -> OrganisationMember:
    """Dependency helper — user must be an admin of the org."""
    membership = _require_member(org_id, current_user, db)
    if membership.role != OrgRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can perform this action",
        )
    return membership


def _build_org_response(org: Organisation, db: Session) -> OrgResponse:
    """Construct an OrgResponse enriched with the live member count."""
    member_count = (
        db.query(OrganisationMember)
        .filter(OrganisationMember.org_id == org.id)
        .count()
    )
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=member_count,
    )


def _build_member_response(m: OrganisationMember) -> OrgMemberResponse:
    """Build an OrgMemberResponse from a membership record + its user."""
    return OrgMemberResponse(
        user_id=m.user.id,
        email=m.user.email,
        full_name=m.user.full_name,
        role=m.role,
        joined_at=m.joined_at,
        invited_at=m.invited_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
def create_org(
    payload: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organisation.

    The calling user automatically becomes the org's first admin and their
    ``org_id`` is updated to the new organisation.

    Args:
        payload: Organisation creation payload (name + optional slug).
        db: Database session.
        current_user: Authenticated user who becomes the admin.

    Returns:
        The created organisation.

    Raises:
        HTTPException 400: If the user already belongs to another org.
        HTTPException 409: If the slug is already taken.
    """
    if current_user.org_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already belong to an organisation. Leave it before creating a new one.",
        )

    slug = payload.slug or _slugify(payload.name)

    # Ensure uniqueness; if auto-generated slug collides, append the user id
    existing_slug = db.query(Organisation).filter(Organisation.slug == slug).first()
    if existing_slug:
        if payload.slug:
            # User explicitly provided it — that's a conflict
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The slug '{slug}' is already taken. Please choose a different one.",
            )
        slug = f"{slug}-{current_user.id}"

    org = Organisation(
        name=payload.name,
        slug=slug,
        owner_id=current_user.id,
    )
    db.add(org)
    db.flush()  # Get org.id before creating membership

    # Add creator as admin member
    membership = OrganisationMember(
        org_id=org.id,
        user_id=current_user.id,
        role=OrgRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db.add(membership)

    # Link the user to the org
    current_user.org_id = org.id
    db.merge(current_user)

    db.commit()
    db.refresh(org)

    return _build_org_response(org, db)


@router.get("/{org_id}", response_model=OrgResponse)
def get_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return organisation details.

    Args:
        org_id: ID of the organisation to retrieve.
        db: Database session.
        current_user: Must be a member of the org.

    Returns:
        Organisation details including live member count.

    Raises:
        HTTPException 403: If the user is not a member.
        HTTPException 404: If the org does not exist.
    """
    org = _get_org_or_404(org_id, db)
    _require_member(org_id, current_user, db)
    return _build_org_response(org, db)


@router.patch("/{org_id}", response_model=OrgResponse)
def update_org(
    org_id: int,
    payload: OrgUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update organisation name (admin only).

    Args:
        org_id: ID of the organisation to update.
        payload: Fields to update (currently only name).
        db: Database session.
        current_user: Must be an org admin.

    Returns:
        The updated organisation.

    Raises:
        HTTPException 403: If the user is not an admin.
        HTTPException 404: If the org does not exist.
    """
    org = _get_org_or_404(org_id, db)
    _require_admin(org_id, current_user, db)

    if payload.name is not None:
        org.name = payload.name

    db.commit()
    db.refresh(org)
    return _build_org_response(org, db)


@router.get("/{org_id}/members", response_model=OrgMemberListResponse)
def list_members(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all members of an organisation.

    Args:
        org_id: ID of the organisation.
        db: Database session.
        current_user: Must be a member of the org.

    Returns:
        OrgMemberListResponse containing all member records.

    Raises:
        HTTPException 403: If the user is not a member.
        HTTPException 404: If the org does not exist.
    """
    _get_org_or_404(org_id, db)
    _require_member(org_id, current_user, db)

    memberships = (
        db.query(OrganisationMember)
        .filter(OrganisationMember.org_id == org_id)
        .all()
    )

    members = [_build_member_response(m) for m in memberships]
    return OrgMemberListResponse(members=members, total=len(members))


@router.post("/{org_id}/members", response_model=OrgMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    org_id: int,
    payload: InviteMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite an existing AegisAI user to the organisation by email.

    The invited user's ``org_id`` is updated immediately; a ``joined_at``
    timestamp is set to indicate they have been added directly (no email
    confirmation flow is required in this version).

    Args:
        org_id: ID of the organisation.
        payload: Invitation payload containing the target user's email.
        db: Database session.
        current_user: Must be an org admin.

    Returns:
        The created membership record.

    Raises:
        HTTPException 400: If the user is already in an org.
        HTTPException 403: If the caller is not an admin.
        HTTPException 404: If the org or target user does not exist.
        HTTPException 409: If the user is already a member.
    """
    _get_org_or_404(org_id, db)
    _require_admin(org_id, current_user, db)

    target_user = db.query(User).filter(User.email == payload.email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email '{payload.email}'",
        )

    if target_user.org_id is not None and target_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user already belongs to a different organisation",
        )

    existing = _get_membership(org_id, target_user.id, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organisation",
        )

    membership = OrganisationMember(
        org_id=org_id,
        user_id=target_user.id,
        role=OrgRole.MEMBER,
        joined_at=datetime.utcnow(),
    )
    db.add(membership)

    # Update the invited user's org_id
    target_user.org_id = org_id
    db.merge(target_user)

    db.commit()
    db.refresh(membership)

    return _build_member_response(membership)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from the organisation.

    Org owners cannot remove themselves — transfer ownership first.

    Args:
        org_id: ID of the organisation.
        user_id: ID of the user to remove.
        db: Database session.
        current_user: Must be an org admin.

    Returns:
        HTTP 204 No Content on success.

    Raises:
        HTTPException 400: If attempting to remove the org owner.
        HTTPException 403: If the caller is not an admin.
        HTTPException 404: If the org, the target user, or the membership does not exist.
    """
    org = _get_org_or_404(org_id, db)
    _require_admin(org_id, current_user, db)

    if user_id == org.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the organisation owner. Transfer ownership before removing.",
        )

    membership = _get_membership(org_id, user_id, db)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organisation",
        )

    # Clear the user's org_id
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.org_id = None
        db.merge(target_user)

    db.delete(membership)
    db.commit()
