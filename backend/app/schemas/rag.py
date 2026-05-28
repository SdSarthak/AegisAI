"""Pydantic schemas for RAG Intelligence endpoints."""

from typing import Optional

from pydantic import BaseModel, Field

RAG_QUESTION_MAX_LENGTH = 2000


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=RAG_QUESTION_MAX_LENGTH)


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None
    groundedness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite groundedness score (0.0-1.0). Higher = more grounded.",
    )
    low_confidence: bool = Field(
        default=False,
        description="True when groundedness_score is below the configured threshold.",
    )
    confidence_tier: str = Field(
        default="unknown",
        description="'high' (>=0.80) | 'medium' (>=threshold) | 'low' (<threshold)",
    )
    per_verifier_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Scores per verifier: semantic, retrieval, lexical.",
    )
    flagged_reason: Optional[str] = Field(
        default=None,
        description="Human-readable reason when low_confidence is True.",
    )
