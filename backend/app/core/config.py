from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DOCUMENT_SHARE_EXPIRE_DAYS: int = 7
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
    LLM_API_KEY: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "llama3.2"
    LLM_TIMEOUT: float = 30.0

    # Module 2: LLM Guard
    GUARD_SANITIZATION_LEVEL: str = "medium"
    GUARD_MAX_PROMPT_LENGTH: int = 2000
    GUARD_RATE_LIMIT_REQUESTS: int = 60
    GUARD_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Rate Limiting & Outage Policies
    RATE_LIMIT_FAIL_CLOSED: bool = False
    BADGE_RATE_LIMIT_REQUESTS: int = 5
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
    FAISS_INDEX_BASE_PATH: str = "faiss_data"
    MLFLOW_TRACKING_URI: str = ""
    EMBEDDINGS_MODEL: str = "nomic-embed-text"
    RAG_MAX_FILES_PER_REQUEST: int = 10
    RAG_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
    RAG_TOTAL_BUDGET_BYTES: int = 50 * 1024 * 1024

    # Observability (OpenTelemetry)
    OTEL_SERVICE_NAME: str = "aegis-backend"
    OTEL_METRICS_EXPORTER: str = "prometheus"
    OTEL_TRACES_EXPORTER: str = "none"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
