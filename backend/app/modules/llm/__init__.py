"""LLM client module for OpenAI-compatible API integration.

The package exports the provider-agnostic ``LLMClient`` wrapper used by the
RAG and document-generation flows.
"""

from .llm_client import LLMClient

__all__ = ["LLMClient"]
