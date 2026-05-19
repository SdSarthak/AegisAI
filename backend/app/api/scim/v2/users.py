from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.scim import SCIMUserCreate, SCIMUserResponse, SCIMError, SCIMListResponse
from app.models.user import User

router = APIRouter()

class SCIMResponse(JSONResponse):
    media_type = "application/scim+json"

def scim_error(detail: str, status_code: int) -> SCIMResponse:
    content = SCIMError(detail=detail, status=str(status_code)).dict()
    return SCIMResponse(content=content, status_code=status_code)

def build_scim_user(user: User) -> dict:
    name_parts = (user.full_name or "").split(" ")
    given_name = name_parts[0] if len(name_parts) > 0 else ""
    family_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    return SCIMUserResponse(
        id=str(user.id),
        userName=user.email,
        name={
            "formatted": user.full_name,
            "givenName": given_name,
            "familyName": family_name
        },
        emails=[{"value": user.email, "primary": True}],
        active=user.is_active,
        externalId=user.scim_external_id,
        meta={"resourceType": "User", "location": f"/scim/v2/Users/{user.id}"}
    ).dict()

@router.get("/Users", response_class=SCIMResponse)
def get_users(filter: str = None, db: Session = Depends(get_db)):
    query = db.query(User)
    
    # Very basic filter parsing for Okta check: filter=userName eq "test@test.com"
    if filter and "userName eq" in filter:
        email = filter.split("eq")[-1].strip().strip('"').strip("'")
        query = query.filter(User.email == email)
        
    users = query.all()
    
    resources = [build_scim_user(u) for u in users]
    
    content = SCIMListResponse(
        totalResults=len(resources),
        itemsPerPage=len(resources) if len(resources) > 0 else 0,
        startIndex=1,
        Resources=resources
    ).dict()
    return content

@router.post("/Users", response_class=SCIMResponse, status_code=201)
def create_user(user_in: SCIMUserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.userName).first()
    if existing_user:
        return scim_error("User already exists", 409)

    full_name = user_in.name.formatted or f"{user_in.name.givenName or ''} {user_in.name.familyName or ''}".strip()
    
    new_user = User(
        email=user_in.userName,
        full_name=full_name,
        hashed_password="IDP_PROVISIONED_NO_PASSWORD", 
        is_active=user_in.active,
        scim_external_id=user_in.externalId
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_scim_user(new_user)

@router.get("/Users/{user_id}", response_class=SCIMResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return scim_error("User not found", 404)
    return build_scim_user(user)

@router.put("/Users/{user_id}", response_class=SCIMResponse)
def update_user(user_id: int, user_in: SCIMUserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return scim_error("User not found", 404)
        
    user.email = user_in.userName
    user.full_name = user_in.name.formatted or f"{user_in.name.givenName or ''} {user_in.name.familyName or ''}".strip()
    user.is_active = user_in.active
    user.scim_external_id = user_in.externalId
    
    db.commit()
    db.refresh(user)
    return build_scim_user(user)

from fastapi import Body

@router.patch("/Users/{user_id}", response_class=SCIMResponse)
def patch_user(user_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return scim_error("User not found", 404)

    operations = body.get("Operations", [])
    for op in operations:
        action = op.get("op", "").lower()
        path = op.get("path", "")
        value = op.get("value")

        if action == "replace":
            if path == "active":
                user.is_active = bool(value)
            elif path == "userName":
                user.email = value
            elif path == "name.givenName" or path == "name.familyName":
                # Basic handling
                pass

    db.commit()
    db.refresh(user)
    return build_scim_user(user)

@router.delete("/Users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return scim_error("User not found", 404)
    db.delete(user)
    db.commit()
    return None

