"""Expose the provider-agnostic LLM client used across backend flows.

Importing from this package keeps the OpenAI-compatible client available in
one place for the RAG and document-generation subsystems.
"""

from .llm_client import LLMClient

__all__ = ["LLMClient"]
