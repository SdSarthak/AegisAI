"""Cosine grounding score for RAG answers.

Changed: Added a production RAG grounding checker based on answer-to-chunk embeddings.
Why: RAG responses need an explicit support score in the API contract.
Addresses: Hallucinated or weakly supported answers by surfacing LOW/MEDIUM/HIGH grounding.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

EmbeddingsFn = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class GroundingResult:
    """Grounding result returned for a generated RAG answer."""

    score: float
    confidence: str
    warning: Optional[str] = None


class GroundingChecker:
    """Measure how well an answer is supported by retrieved chunks."""

    def __init__(self, embeddings_fn: Optional[EmbeddingsFn] = None) -> None:
        """Initialize the checker with an optional embedding function.

        Args:
            embeddings_fn: Callable that embeds a list of texts. When omitted,
                the configured project embedding model is loaded lazily.
        """
        self.embeddings_fn = embeddings_fn or self._load_default_embeddings_fn()

    def check(self, answer: str, chunks: list[str]) -> GroundingResult:
        """Return the average top-3 answer-to-chunk cosine grounding score.

        Args:
            answer: LLM-generated answer text.
            chunks: Retrieved context chunks used to answer the question.

        Returns:
            GroundingResult with score, confidence label, and optional warning.
        """
        if not answer.strip() or not chunks:
            return self._result_for_score(0.0)

        texts = [answer] + chunks
        try:
            embeddings = self.embeddings_fn(texts)
        except Exception:
            logger.exception("Grounding embeddings failed")
            return self._result_for_score(0.0)

        if len(embeddings) < 2:
            return self._result_for_score(0.0)

        answer_embedding = embeddings[0]
        chunk_embeddings = embeddings[1:]
        similarities = [
            _cosine_similarity(answer_embedding, chunk_embedding)
            for chunk_embedding in chunk_embeddings
        ]
        top_scores = sorted(similarities, reverse=True)[:3]
        score = sum(top_scores) / len(top_scores) if top_scores else 0.0
        return self._result_for_score(_clamp_score(score))

    def _load_default_embeddings_fn(self) -> EmbeddingsFn:
        """Load the same embeddings configured for the FAISS vector store."""
        from app.modules.rag.vector_store import get_embeddings

        embeddings = get_embeddings()
        if hasattr(embeddings, "embed_documents"):
            return embeddings.embed_documents
        if callable(embeddings):
            return embeddings
        raise TypeError("Configured embeddings object is not callable")

    def _result_for_score(self, score: float) -> GroundingResult:
        """Map a normalized score to confidence and optional warning."""
        rounded = round(_clamp_score(score), 4)
        if rounded >= 0.75:
            return GroundingResult(score=rounded, confidence="HIGH")
        if rounded >= 0.50:
            return GroundingResult(score=rounded, confidence="MEDIUM")
        return GroundingResult(
            score=rounded,
            confidence="LOW",
            warning=(
                "This answer may not be fully supported by the retrieved context."
            ),
        )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity normalized to the 0.0-1.0 range."""
    if len(left) != len(right) or not left:
        return 0.0

    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
    right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    raw = dot / (left_norm * right_norm)
    return (raw + 1.0) / 2.0


def _clamp_score(score: float) -> float:
    """Clamp finite scores into the 0.0 to 1.0 range."""
    if not math.isfinite(score):
        return 0.0
    return max(0.0, min(1.0, float(score)))
