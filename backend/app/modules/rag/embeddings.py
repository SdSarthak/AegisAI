"""Centralized embedding factory for AegisAI RAG pipeline.

Ensures the same embedding model is used for both document ingestion
and query processing, preventing embedding space incompatibility.
"""

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings():
    """Return the configured embeddings model based on settings."""
    provider = settings.EMBEDDING_PROVIDER

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        base = settings.LLM_BASE_URL or "http://ollama:11434"
        if base.endswith("/v1"):
            base = base[:-3]
        return OllamaEmbeddings(model=settings.EMBEDDINGS_MODEL, base_url=base)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
