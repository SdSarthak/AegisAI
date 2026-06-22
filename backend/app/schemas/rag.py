"""Pydantic schemas for RAG Intelligence endpoints.

Changed: Expanded RAGQueryResponse with guard, chunk-scan, and grounding fields.
Why: Clients need visibility into sanitization, chunk drops, and answer support.
Addresses: Silent prompt-injection handling and hidden hallucination risk.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """Request payload for a RAG query."""

    question: str = Field(..., min_length=1, max_length=2000)


class RAGQueryResponse(BaseModel):
    """Response payload for guarded RAG query results."""

    answer: str
    sources: list[dict[str, Any] | str] = Field(default_factory=list)
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_confidence: str = "LOW"
    guard_triggered: bool = False
    guard_decision: str = "ALLOW"
    chunks_total: int = 0
    chunks_dropped: int = 0
    warning: str | None = None

    # Legacy fields retained as optional compatibility aliases for older clients.
    answer_id: Optional[str] = None
    groundedness_score: float | None = None
    low_confidence: bool | None = None
    confidence_tier: str | None = None
    per_verifier_scores: dict[str, float] = Field(default_factory=dict)
    flagged_reason: Optional[str] = None
