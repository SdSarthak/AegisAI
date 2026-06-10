"""Groundedness scoring for RAG answers against retrieved source chunks."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

EmbeddingsFn = Callable[[list[str]], list[list[float]]]


@dataclass
class GroundednessResult:
    """Composite groundedness result returned by the hybrid checker.

    Attributes:
        groundedness_score: Final aggregated groundedness score.
        low_confidence: Whether the score fell below the configured threshold.
        confidence_tier: Human-readable confidence band.
        per_verifier_scores: Individual verifier scores used in aggregation.
        flagged_reason: Optional explanation for why the result was flagged.
    """

    groundedness_score: float
    low_confidence: bool
    confidence_tier: str
    per_verifier_scores: dict[str, float]
    flagged_reason: Optional[str]


class BaseVerifier(ABC):
    """Abstract base class for groundedness verifier signals.

    Concrete verifiers compare an answer, its sources, and the query to
    produce a normalized confidence score.
    """

    @abstractmethod
    def verify(
        self,
        answer: str,
        chunks: list[str],
        query: str,
        embeddings_fn: EmbeddingsFn,
    ) -> float:
        """Return a verifier score between 0.0 and 1.0.

        Args:
            answer: Generated answer text.
            chunks: Retrieved source chunks.
            query: Original user query.
            embeddings_fn: Callable used to embed text for comparison.
        """


class SemanticSimilarityVerifier(BaseVerifier):
    """Compare the generated answer to retrieved chunks with cosine similarity.

    This signal rewards answers that semantically resemble the retrieved
    source chunks.
    """

    def verify(
        self,
        answer: str,
        chunks: list[str],
        query: str,
        embeddings_fn: EmbeddingsFn,
    ) -> float:
        """Return the maximum answer-to-chunk cosine similarity.

        Args:
            answer: Generated answer text.
            chunks: Retrieved source chunks.
            query: Original user query.
            embeddings_fn: Callable used to embed text for comparison.

        Returns:
            The strongest answer-to-chunk similarity score.
        """
        del query
        if not answer.strip() or not chunks:
            return 0.0

        texts = [answer] + chunks
        try:
            embeddings = embeddings_fn(texts)
        except Exception:
            logger.warning("Semantic groundedness embeddings failed", exc_info=True)
            return 0.0

        if len(embeddings) < 2:
            return 0.0

        answer_embedding = np.asarray(embeddings[0], dtype=float)
        chunk_embeddings = [
            np.asarray(embedding, dtype=float) for embedding in embeddings[1:]
        ]
        similarities = [
            _cosine_similarity(answer_embedding, chunk_embedding)
            for chunk_embedding in chunk_embeddings
        ]
        return max(similarities, default=0.0)


class RetrievalRelevanceVerifier(BaseVerifier):
    """Compare the user query to retrieved chunks with cosine similarity.

    This signal rewards retrieval results that stay close to the original
    user question.
    """

    def verify(
        self,
        answer: str,
        chunks: list[str],
        query: str,
        embeddings_fn: EmbeddingsFn,
    ) -> float:
        """Return the mean query-to-chunk cosine similarity.

        Args:
            answer: Generated answer text.
            chunks: Retrieved source chunks.
            query: Original user query.
            embeddings_fn: Callable used to embed text for comparison.

        Returns:
            The average query-to-chunk similarity score.
        """
        del answer
        if not query.strip() or not chunks:
            return 0.0

        texts = [query] + chunks
        try:
            embeddings = embeddings_fn(texts)
        except Exception:
            logger.warning("Retrieval groundedness embeddings failed", exc_info=True)
            return 0.0

        if len(embeddings) < 2:
            return 0.0

        query_embedding = np.asarray(embeddings[0], dtype=float)
        chunk_embeddings = [
            np.asarray(embedding, dtype=float) for embedding in embeddings[1:]
        ]
        similarities = [
            _cosine_similarity(query_embedding, chunk_embedding)
            for chunk_embedding in chunk_embeddings
        ]
        if not similarities:
            return 0.0
        return float(np.mean(similarities))


class LexicalOverlapVerifier(BaseVerifier):
    """Compare answer and chunk terms with stop-word-filtered Jaccard overlap.

    This signal provides a lightweight lexical sanity check on top of the
    semantic verifiers.
    """

    _TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9]{2,}\b")
    _STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "under",
        "was",
        "were",
        "with",
    }

    def verify(
        self,
        answer: str,
        chunks: list[str],
        query: str,
        embeddings_fn: EmbeddingsFn,
    ) -> float:
        """Return Jaccard similarity between answer tokens and chunk tokens.

        Args:
            answer: Generated answer text.
            chunks: Retrieved source chunks.
            query: Original user query.
            embeddings_fn: Callable used to embed text for comparison.

        Returns:
            A token-overlap score between the answer and retrieved chunks.
        """
        del query, embeddings_fn
        answer_tokens = self._tokenize(answer)
        chunk_tokens = self._tokenize(" ".join(chunks))
        if not answer_tokens or not chunk_tokens:
            return 0.0

        intersection = answer_tokens.intersection(chunk_tokens)
        union = answer_tokens.union(chunk_tokens)
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def _tokenize(self, text: str) -> set[str]:
        """Return normalized non-stop-word tokens from text."""
        return {
            token.lower()
            for token in self._TOKEN_PATTERN.findall(text)
            if token.lower() not in self._STOP_WORDS
        }


@dataclass
class GroundednessConfig:
    """Configuration for the hybrid groundedness checker.

    The weights are normalized internally before aggregation.
    """

    low_confidence_threshold: float = 0.65
    semantic_weight: float = 0.50
    retrieval_weight: float = 0.30
    lexical_weight: float = 0.20


class HybridGroundednessChecker:
    """Run multiple verifier signals and aggregate them into one confidence score.

    The checker combines semantic, retrieval, and lexical signals into a
    single groundedness result that the RAG layer can expose.
    """

    def __init__(
        self,
        embeddings_fn: EmbeddingsFn,
        config: Optional[GroundednessConfig] = None,
        extra_verifiers: Optional[list[tuple[str, BaseVerifier, float]]] = None,
    ) -> None:
        """Initialize the checker with embeddings, config, and optional verifiers.

        Args:
            embeddings_fn: Callable used to embed text during verification.
            config: Optional weighting and threshold configuration.
            extra_verifiers: Optional additional named verifier tuples.
        """
        self.embeddings_fn = embeddings_fn
        self.config = config or GroundednessConfig()
        self.verifiers: list[tuple[str, BaseVerifier, float]] = [
            ("semantic", SemanticSimilarityVerifier(), self.config.semantic_weight),
            ("retrieval", RetrievalRelevanceVerifier(), self.config.retrieval_weight),
            ("lexical", LexicalOverlapVerifier(), self.config.lexical_weight),
        ]
        self.verifiers.extend(extra_verifiers or [])

    def check(self, answer: str, chunks: list[str], query: str) -> GroundednessResult:
        """Return the hybrid groundedness result for an answer and its sources.

        Args:
            answer: Generated answer text.
            chunks: Retrieved source chunks.
            query: Original user query.

        Returns:
            GroundednessResult describing the aggregated groundedness score.
        """
        per_verifier_scores: dict[str, float] = {}
        weighted_score = 0.0
        total_weight = 0.0

        for name, verifier, weight in self.verifiers:
            try:
                raw_score = verifier.verify(answer, chunks, query, self.embeddings_fn)
                score = _clamp_score(raw_score)
            except Exception:
                logger.warning("Groundedness verifier '%s' failed", name, exc_info=True)
                score = 0.0

            rounded_score = round(score, 4)
            per_verifier_scores[name] = rounded_score
            weighted_score += weight * score
            total_weight += weight

        composite = weighted_score / total_weight if total_weight else 0.0
        composite = round(_clamp_score(composite), 4)
        threshold = self.config.low_confidence_threshold
        low_confidence = composite < threshold
        confidence_tier = _confidence_tier(composite, threshold)
        flagged_reason = None

        if low_confidence:
            weakest_name = min(
                per_verifier_scores,
                key=lambda name: per_verifier_scores[name],
            )
            weakest_score = per_verifier_scores[weakest_name]
            flagged_reason = (
                f"Low groundedness: weakest verifier '{weakest_name}' "
                f"scored {weakest_score:.4f}."
            )
            logger.info(
                "Low groundedness detected: score=%s weakest=%s",
                composite,
                weakest_name,
            )

        return GroundednessResult(
            groundedness_score=composite,
            low_confidence=low_confidence,
            confidence_tier=confidence_tier,
            per_verifier_scores=per_verifier_scores,
            flagged_reason=flagged_reason,
        )


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Backward-compatible public cosine similarity helper for legacy tests.

    Args:
        left: First vector.
        right: Second vector.

    Returns:
        Cosine similarity between the vectors.
    """
    return _cosine_similarity(
        np.asarray(left, dtype=float),
        np.asarray(right, dtype=float),
    )


def get_embeddings():
    """Lazy embeddings wrapper retained for older groundedness callers/tests.

    Returns:
        The configured embeddings implementation.
    """
    from .vector_store import get_embeddings as loader

    return loader()


def compute_groundedness(answer: str, chunks: list[str]) -> float:
    """Return the legacy answer-to-source groundedness score.

    Args:
        answer: Generated answer text.
        chunks: Retrieved source chunks.

    Returns:
        A legacy groundedness score between 0.0 and 1.0.
    """
    if not answer.strip() or not chunks:
        return 0.0

    try:
        embeddings = get_embeddings()
        answer_embedding = embeddings.embed_query(answer)
        source_embedding = embeddings.embed_query("\n\n".join(chunks))
    except Exception:
        logger.warning("Legacy groundedness computation failed", exc_info=True)
        return 0.0

    return _clamp_score(cosine_similarity(answer_embedding, source_embedding))


def _clamp_score(score: float) -> float:
    """Clamp a similarity score to the 0.0-1.0 range."""
    if not np.isfinite(score):
        return 0.0
    return max(0.0, min(1.0, float(score)))


def _confidence_tier(score: float, threshold: float) -> str:
    """Map a groundedness score to a human-readable confidence tier."""
    if score >= 0.80:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"
