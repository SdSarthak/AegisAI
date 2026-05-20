from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any

class SCIMEmail(BaseModel):
    value: EmailStr
    type: str = "work"
    primary: bool = True

class SCIMName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None

class SCIMUserCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: SCIMName
    emails: List[SCIMEmail]
    active: bool = True
    externalId: Optional[str] = None

class SCIMUserResponse(SCIMUserCreate):
    id: str
    meta: dict

class SCIMError(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    detail: str
    status: str

class SCIMListResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    itemsPerPage: int
    startIndex: int
    Resources: List[Any]

class SCIMGroupCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    displayName: str
    members: Optional[List[dict]] = []
    externalId: Optional[str] = None

class SCIMGroupResponse(SCIMGroupCreate):
    id: str
    meta: dict
