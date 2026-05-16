from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AegisAI"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/aegisai_db"

    # JWT
    SECRET_KEY: str = "change-this-in-production"
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

    # LLM provider — OpenAI-compatible (works with OpenAI, Ollama, Groq, Together AI, vLLM …)
    # Ollama (free, local): LLM_API_KEY=ollama  LLM_BASE_URL=http://localhost:11434/v1
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = (
        ""  # Leave empty for OpenAI default; set for any compatible endpoint
    )
    LLM_MODEL: str = "gpt-4o-mini"  # Model name understood by your chosen provider

    # Module 2: LLM Guard
    GUARD_SANITIZATION_LEVEL: str = "medium"  # low | medium | high
    GUARD_MAX_PROMPT_LENGTH: int = 2000

    # Module 3: RAG Intelligence
    S3_BUCKET_NAME: str = ""
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    FAISS_INDEX_PATH: str = "faiss_index"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
