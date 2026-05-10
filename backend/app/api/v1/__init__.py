from fastapi import APIRouter
from app.api.v1 import auth, ai_systems, documents, classification, guard, rag

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(auth.users_router, prefix="/users", tags=["Users"])
api_router.include_router(ai_systems.router, prefix="/ai-systems", tags=["AI Systems"])
api_router.include_router(classification.router, prefix="/classification", tags=["Risk Classification"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(guard.router, prefix="/guard", tags=["LLM Guard"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Intelligence"])
