from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.scim import SCIMGroupCreate, SCIMGroupResponse, SCIMError, SCIMListResponse

router = APIRouter()

class SCIMResponse(JSONResponse):
    media_type = "application/scim+json"

def scim_error(detail: str, status_code: int) -> SCIMResponse:
    content = SCIMError(detail=detail, status=str(status_code)).dict()
    return SCIMResponse(content=content, status_code=status_code)

@router.get("/Groups", response_class=SCIMResponse)
def get_groups(db: Session = Depends(get_db)):
    # Currently AegisAI does not have a formal Group model.
    # Returning an empty list of groups for standard compliance.
    content = SCIMListResponse(
        totalResults=0,
        itemsPerPage=0,
        startIndex=1,
        Resources=[]
    ).dict()
    return content

@router.post("/Groups", response_class=SCIMResponse, status_code=201)
def create_group(group_in: SCIMGroupCreate, db: Session = Depends(get_db)):
    # Mocking group creation since AegisAI uses roles instead of strict groups right now.
    # We will just echo back the group to satisfy IdP provisions.
    group_id = "mock-group-id"
    return SCIMGroupResponse(
        id=group_id,
        displayName=group_in.displayName,
        members=group_in.members,
        externalId=group_in.externalId,
        meta={"resourceType": "Group", "location": f"/scim/v2/Groups/{group_id}"}
    ).dict()
