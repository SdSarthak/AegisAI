from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AegisAI"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Stripe (optional — leave blank to disable billing)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_SCALE: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM provider
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Module 2: LLM Guard
    GUARD_SANITIZATION_LEVEL: str = "medium"
    GUARD_MAX_PROMPT_LENGTH: int = 2000
    GUARD_RATE_LIMIT_REQUESTS: int = 60
    GUARD_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Module 1: Public Badge API
    BADGE_RATE_LIMIT_REQUESTS: int = 30
    BADGE_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Shared infrastructure
    REDIS_URL: str = ""

    # Module 1: AI System bulk import
    AI_SYSTEM_BULK_IMPORT_MAX_BYTES: int = 5 * 1024 * 1024
    AI_SYSTEM_BULK_IMPORT_MAX_ROWS: int = 5000

    # Module 3: RAG Intelligence
    S3_BUCKET_NAME: str = ""
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    FAISS_INDEX_PATH: str = "faiss_index"
    MLFLOW_TRACKING_URI: str = ""

    # MLflow
    MLFLOW_TRACKING_URI: Optional[str] = None  # ← only line added

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()