from fastapi import APIRouter, Depends
from app.api.scim.v2 import users, groups
from app.api.scim.v2.dependencies import verify_scim_token

scim_v2_router = APIRouter(dependencies=[Depends(verify_scim_token)])

scim_v2_router.include_router(users.router, tags=["SCIM 2.0 Users"])
scim_v2_router.include_router(groups.router, tags=["SCIM 2.0 Groups"])
