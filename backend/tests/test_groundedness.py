"""Tests for RAG groundedness verification."""

from unittest.mock import MagicMock

import pytest

from app.modules.rag.groundedness import (
    BaseVerifier,
    GroundednessConfig,
    HybridGroundednessChecker,
    LexicalOverlapVerifier,
    RetrievalRelevanceVerifier,
    SemanticSimilarityVerifier,
)
from app.schemas.rag import RAGQueryResponse


def _embedding_fn(vectors):
    def embed(texts):
        return vectors[: len(texts)]

    return embed


class ScoreVerifier(BaseVerifier):
    """Test verifier that returns a fixed score."""

    def __init__(self, score):
        self.score = score
        self.called = False

    def verify(self, answer, chunks, query, embeddings_fn):
        self.called = True
        return self.score


class ThrowingVerifier(BaseVerifier):
    """Test verifier that raises to exercise checker isolation."""

    def verify(self, answer, chunks, query, embeddings_fn):
        raise RuntimeError("verifier failed")


class TestSemanticSimilarityVerifier:
    """Unit tests for semantic answer-to-chunk similarity."""

    def test_close_answer_scores_high(self):
        verifier = SemanticSimilarityVerifier()
        score = verifier.verify(
            "high risk systems need assessment",
            ["high risk systems require assessment"],
            "query",
            _embedding_fn([[1.0, 0.0], [0.9, 0.1]]),
        )
        assert score > 0.7

    def test_distant_answer_scores_low(self):
        verifier = SemanticSimilarityVerifier()
        score = verifier.verify(
            "high risk systems need assessment",
            ["unrelated weather forecast"],
            "query",
            _embedding_fn([[1.0, 0.0], [0.0, 1.0]]),
        )
        assert score < 0.4

    def test_empty_answer_returns_zero(self):
        verifier = SemanticSimilarityVerifier()
        score = verifier.verify("", ["chunk"], "query", _embedding_fn([[1.0], [1.0]]))
        assert score == 0.0

    def test_empty_chunks_returns_zero(self):
        verifier = SemanticSimilarityVerifier()
        score = verifier.verify("answer", [], "query", _embedding_fn([[1.0]]))
        assert score == 0.0

    def test_embeddings_exception_returns_zero(self):
        def raises(texts):
            raise RuntimeError("boom")

        verifier = SemanticSimilarityVerifier()
        score = verifier.verify("answer", ["chunk"], "query", raises)
        assert score == 0.0


class TestRetrievalRelevanceVerifier:
    """Unit tests for query-to-chunk retrieval relevance."""

    def test_relevant_chunks_score_high(self):
        verifier = RetrievalRelevanceVerifier()
        score = verifier.verify(
            "answer",
            ["article 43 conformity", "high risk assessment"],
            "article 43 conformity assessment",
            _embedding_fn([[1.0, 0.0], [0.9, 0.1], [0.8, 0.2]]),
        )
        assert score > 0.6

    def test_irrelevant_chunks_score_low(self):
        verifier = RetrievalRelevanceVerifier()
        score = verifier.verify(
            "answer",
            ["unrelated", "other"],
            "article 43 conformity assessment",
            _embedding_fn([[1.0, 0.0], [0.0, 1.0], [0.1, 0.9]]),
        )
        assert score < 0.4

    def test_empty_query_returns_zero(self):
        verifier = RetrievalRelevanceVerifier()
        score = verifier.verify("answer", ["chunk"], "", _embedding_fn([[1.0], [1.0]]))
        assert score == 0.0


class TestLexicalOverlapVerifier:
    """Unit tests for lexical overlap."""

    def test_high_overlap_scores_high(self):
        verifier = LexicalOverlapVerifier()
        score = verifier.verify(
            "High risk AI systems require conformity assessment",
            ["High risk AI systems require conformity assessment"],
            "query",
            MagicMock(),
        )
        assert score > 0.5

    def test_zero_overlap_scores_zero(self):
        verifier = LexicalOverlapVerifier()
        score = verifier.verify("alpha beta", ["gamma delta"], "query", MagicMock())
        assert score == 0.0

    def test_stop_words_only_answer_returns_zero(self):
        verifier = LexicalOverlapVerifier()
        score = verifier.verify(
            "a an the is are of in on", ["regulatory chunk"], "query", MagicMock()
        )
        assert score == 0.0

    def test_does_not_call_embeddings_fn(self):
        embeddings_fn = MagicMock()
        verifier = LexicalOverlapVerifier()
        verifier.verify(
            "article conformity", ["article conformity"], "query", embeddings_fn
        )
        embeddings_fn.assert_not_called()


class TestHybridGroundednessChecker:
    """Unit tests for hybrid aggregation."""

    def test_all_verifiers_high(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.9), 0.5),
            ("retrieval", ScoreVerifier(0.85), 0.3),
            ("lexical", ScoreVerifier(0.8), 0.2),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.groundedness_score > 0.7
        assert result.low_confidence is False
        assert result.confidence_tier == "high"

    def test_all_verifiers_low(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.1), 0.5),
            ("retrieval", ScoreVerifier(0.2), 0.3),
            ("lexical", ScoreVerifier(0.3), 0.2),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.groundedness_score < 0.65
        assert result.low_confidence is True
        assert result.confidence_tier == "low"

    def test_mixed_scores_weighted_average(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.8), 0.5),
            ("retrieval", ScoreVerifier(0.4), 0.3),
            ("lexical", ScoreVerifier(0.2), 0.2),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.groundedness_score == pytest.approx(0.56)

    def test_one_verifier_throws_others_still_run(self):
        retrieval = ScoreVerifier(0.8)
        lexical = ScoreVerifier(0.7)
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ThrowingVerifier(), 0.5),
            ("retrieval", retrieval, 0.3),
            ("lexical", lexical, 0.2),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.groundedness_score == pytest.approx(0.38)
        assert retrieval.called is True
        assert lexical.called is True

    def test_extra_verifiers_included_in_weighted_average(self):
        checker = HybridGroundednessChecker(
            _embedding_fn([]),
            config=GroundednessConfig(
                semantic_weight=0.0,
                retrieval_weight=0.0,
                lexical_weight=0.0,
            ),
            extra_verifiers=[("extra", ScoreVerifier(0.42), 1.0)],
        )
        result = checker.check("answer", ["chunk"], "query")
        assert result.groundedness_score == pytest.approx(0.42)
        assert result.per_verifier_scores["extra"] == pytest.approx(0.42)

    def test_flagged_reason_none_when_not_low_confidence(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.9), 1.0),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.flagged_reason is None

    def test_flagged_reason_set_when_low_confidence(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.1), 1.0),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert result.flagged_reason

    def test_flagged_reason_names_weakest_verifier(self):
        checker = HybridGroundednessChecker(_embedding_fn([]))
        checker.verifiers = [
            ("semantic", ScoreVerifier(0.4), 0.5),
            ("retrieval", ScoreVerifier(0.1), 0.3),
            ("lexical", ScoreVerifier(0.2), 0.2),
        ]
        result = checker.check("answer", ["chunk"], "query")
        assert "retrieval" in result.flagged_reason


def test_rag_response_contains_groundedness_fields_without_losing_existing_keys():
    fake_result = {
        "result": "Article 43 requires conformity assessment.",
        "source_documents": [],
        "groundedness_score": 0.81,
        "low_confidence": False,
        "confidence_tier": "high",
        "per_verifier_scores": {"semantic": 0.9, "retrieval": 0.8, "lexical": 0.6},
        "flagged_reason": None,
    }
    response = RAGQueryResponse(
        answer=fake_result["result"],
        sources=["eu_ai_act.pdf"],
        answer_id="answer-1",
        groundedness_score=fake_result["groundedness_score"],
        low_confidence=fake_result["low_confidence"],
        confidence_tier=fake_result["confidence_tier"],
        per_verifier_scores=fake_result["per_verifier_scores"],
        flagged_reason=fake_result["flagged_reason"],
    )
    data = response.model_dump()

    for key in ("answer", "sources", "answer_id"):
        assert key in data
    for key in (
        "groundedness_score",
        "low_confidence",
        "confidence_tier",
        "per_verifier_scores",
        "flagged_reason",
    ):
        assert key in data


def test_single_empty_chunk_edge_case_returns_result():
    checker = HybridGroundednessChecker(_embedding_fn([[1.0, 0.0], [0.0, 0.0]]))
    result = checker.check("answer", [""], "query")
    assert 0.0 <= result.groundedness_score <= 1.0


def test_whitespace_answer_edge_case_returns_low_confidence():
    checker = HybridGroundednessChecker(_embedding_fn([[0.0, 0.0], [1.0, 0.0]]))
    result = checker.check("   ", ["chunk"], "query")
    assert result.groundedness_score < 0.65
    assert result.low_confidence is True


def test_zero_vectors_do_not_divide_by_zero():
    checker = HybridGroundednessChecker(
        _embedding_fn([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    )
    result = checker.check("answer", ["chunk"], "query")
    assert 0.0 <= result.groundedness_score <= 1.0
