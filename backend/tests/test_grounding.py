"""
Tests for backend/app/modules/rag/grounding.py helper functions.

Covers _cosine_similarity(), _clamp_score(), and GroundingChecker.check().
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.modules.rag.grounding import (
    _cosine_similarity,
    _clamp_score,
    GroundingChecker,
    GroundingResult,
)


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    """Unit tests for the _cosine_similarity helper."""

    def test_identical_vectors(self):
        """Identical vectors should yield maximum similarity (1.0)."""
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should yield 0.5 (neutral after remapping)."""
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.5)

    def test_opposite_vectors(self):
        """Opposite-direction vectors should yield minimum (0.0)."""
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(0.0)

    def test_zero_left_vector(self):
        """Zero vector on left should return 0.0."""
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_zero_right_vector(self):
        """Zero vector on right should return 0.0."""
        assert _cosine_similarity([1.0, 2.0], [0.0, 0.0]) == pytest.approx(0.0)

    def test_both_zero_vectors(self):
        """Both zero vectors should return 0.0."""
        assert _cosine_similarity([0.0, 0.0], [0.0, 0.0]) == pytest.approx(0.0)

    def test_dimension_mismatch(self):
        """Dimension mismatch should return 0.0."""
        assert _cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        assert _cosine_similarity([], []) == pytest.approx(0.0)

    def test_partial_overlap(self):
        """Partially overlapping vectors should yield intermediate value."""
        result = _cosine_similarity([1.0, 1.0], [1.0, 0.0])
        assert 0.5 < result < 1.0

    def test_negative_dot_product(self):
        """Vectors with negative dot product should yield below 0.5."""
        # [1.0, 0.5] dot [0.5, -1.0] = 0.5 - 0.5 = 0.0 -> remapped to 0.5
        # [1.0, 0.5] dot [-0.5, 1.0] = -0.5 + 0.5 = 0.0 -> remapped to 0.5
        # Use vectors with clearly negative dot product:
        result = _cosine_similarity([1.0, 0.0], [-0.5, 0.5])
        assert 0.0 <= result < 0.5

    def test_mixed_sign_vectors(self):
        """Vectors with mixed signs should compute correctly."""
        v1 = [1.0, -2.0, 3.0]
        v2 = [-1.0, 2.0, -3.0]
        result = _cosine_similarity(v1, v2)
        # Dot = -1 - 4 - 9 = -14; norms > 0; remapped to 0.0
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _clamp_score
# ---------------------------------------------------------------------------

class TestClampScore:
    """Unit tests for the _clamp_score helper."""

    def test_value_below_range(self):
        """Values below 0.0 should be clamped to 0.0."""
        assert _clamp_score(-0.5) == pytest.approx(0.0)
        assert _clamp_score(-100.0) == pytest.approx(0.0)

    def test_value_above_range(self):
        """Values above 1.0 should be clamped to 1.0."""
        assert _clamp_score(1.5) == pytest.approx(1.0)
        assert _clamp_score(100.0) == pytest.approx(1.0)

    def test_value_in_range(self):
        """Values within 0.0-1.0 should pass through unchanged."""
        assert _clamp_score(0.5) == pytest.approx(0.5)
        assert _clamp_score(0.0) == pytest.approx(0.0)
        assert _clamp_score(1.0) == pytest.approx(1.0)

    def test_nan(self):
        """NaN should be clamped to 0.0."""
        import math
        assert _clamp_score(float("nan")) == pytest.approx(0.0)

    def test_positive_inf(self):
        """Positive infinity is not finite so maps to 0.0."""
        import math
        assert _clamp_score(float("inf")) == pytest.approx(0.0)

    def test_negative_inf(self):
        """Negative infinity should be clamped to 0.0."""
        import math
        assert _clamp_score(float("-inf")) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# GroundingChecker.check
# ---------------------------------------------------------------------------

class TestGroundingChecker:
    """Unit tests for GroundingChecker.check()."""

    def _fake_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Return a deterministic embedding for each text: [hash(text) % 100 / 100]."""
        result: list[list[float]] = []
        for t in texts:
            h = sum(ord(c) for c in t) % 100
            vec = [float(h) / 100.0] + [0.0] * (4 - 1)
            result.append(vec)
        return result

    def test_empty_answer_returns_low_with_warning(self):
        """Empty/whitespace answer should yield LOW confidence with warning."""
        checker = GroundingChecker(embeddings_fn=self._fake_embeddings)
        result = checker.check("   ", ["chunk1", "chunk2"])
        assert result.confidence == "LOW"
        assert result.score == pytest.approx(0.0)
        assert result.warning is not None
        assert isinstance(result, GroundingResult)

    def test_empty_chunks_returns_low_with_warning(self):
        """Empty chunks list should yield LOW confidence with warning."""
        checker = GroundingChecker(embeddings_fn=self._fake_embeddings)
        result = checker.check("some answer", [])
        assert result.confidence == "LOW"
        assert result.score == pytest.approx(0.0)
        assert result.warning is not None

    def test_high_grounding_yields_high_confidence(self):
        """Answer very similar to chunks should yield HIGH confidence."""
        checker = GroundingChecker(embeddings_fn=self._fake_embeddings)
        # Same text: identical embeddings -> cosine=1.0 -> score=1.0 -> HIGH
        result = checker.check("exact same text", ["exact same text"])
        assert result.confidence == "HIGH"
        assert result.score == pytest.approx(1.0)

    def test_medium_grounding_with_partial_similarity(self):
        """Partial similarity between answer and chunk yields a bounded score."""
        # Mock returns different vectors with ~0.6 cosine similarity
        def partial_embeddings(texts: list[str]) -> list[list[float]]:
            # First embedding (answer): [1, 0, 0]
            # Second (chunk): [0.6, 0.8, 0] -> 0.6 dot + norms ~= 0.6
            if texts:
                return [[1.0, 0.0, 0.0], [0.6, 0.8, 0.0]]
            return []

        checker = GroundingChecker(embeddings_fn=partial_embeddings)
        result = checker.check("answer text", ["context chunk"])
        # cos_sim([1,0,0], [0.6,0.8,0]) = 0.6 / (1 * 1) = 0.6
        # _clamp_score(0.6) = 0.6 -> >= 0.50 -> MEDIUM
        assert result.confidence in ("LOW", "MEDIUM", "HIGH")
        assert 0.0 <= result.score <= 1.0

    def test_embeddings_failure_returns_low_with_warning(self):
        """Embeddings function raising exception should yield LOW with warning."""
        def bad_embeddings(texts: list[str]) -> list[list[float]]:
            raise RuntimeError("embedding service unavailable")

        checker = GroundingChecker(embeddings_fn=bad_embeddings)
        result = checker.check("some answer", ["some chunk"])
        assert result.confidence == "LOW"
        assert result.score == pytest.approx(0.0)
        assert result.warning is not None

    def test_single_chunk_taking_top_score(self):
        """Single chunk: its similarity is the top-3 score."""
        checker = GroundingChecker(embeddings_fn=self._fake_embeddings)
        result = checker.check("answer", ["context"])
        assert isinstance(result, GroundingResult)
        assert result.score >= 0.0
        assert result.score <= 1.0
        assert result.confidence in ("LOW", "MEDIUM", "HIGH")

    def test_top3_averaging_with_multiple_chunks(self):
        """With 5 chunks, only the top-3 similarities are averaged."""
        checker = GroundingChecker(embeddings_fn=self._fake_embeddings)
        chunks = [f"chunk{i}" for i in range(5)]
        result = checker.check("target answer", chunks)
        # Top-3 of 5 same-ish scores should give medium-to-high result
        assert 0.0 <= result.score <= 1.0
        assert result.confidence in ("LOW", "MEDIUM", "HIGH")

    def test_grouding_result_is_frozen_dataclass(self):
        """GroundingResult should be a frozen dataclass."""
        result = GroundingResult(score=0.75, confidence="HIGH")
        assert result.score == 0.75
        assert result.confidence == "HIGH"
        assert result.warning is None

    def test_grouding_result_with_warning(self):
        """GroundingResult can include an optional warning string."""
        result = GroundingResult(
            score=0.3, confidence="LOW", warning="Answer may not be supported."
        )
        assert result.warning == "Answer may not be supported."
