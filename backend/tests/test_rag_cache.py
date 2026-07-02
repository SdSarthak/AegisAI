"""
Unit tests for backend/app/modules/rag/cache.py.

Covers question_hash() stability, user isolation, TTL expiry, and
cache hit/miss behavior.
"""

import pytest
import time
from unittest.mock import patch
from app.modules.rag import cache


class TestQuestionHash:
    """Test question_hash() determinism and user isolation."""

    def test_hash_deterministic(self):
        """Same question and user always produces the same hash."""
        q = "What is the capital of France?"
        user_id = 42
        h1 = cache.question_hash(q, user_id)
        h2 = cache.question_hash(q, user_id)
        assert h1 == h2

    def test_hash_whitespace_normalized(self):
        """Leading/trailing/interior whitespace is collapsed."""
        user_id = 1
        h1 = cache.question_hash("  What is the capital of France?  ", user_id)
        h2 = cache.question_hash("What is the capital of France?", user_id)
        h3 = cache.question_hash("What   is   the   capital   of   France?", user_id)
        assert h1 == h2 == h3

    def test_hash_case_insensitive(self):
        """Hash is case-insensitive."""
        user_id = 1
        h1 = cache.question_hash("What is the capital of France?", user_id)
        h2 = cache.question_hash("what is the capital of france?", user_id)
        h3 = cache.question_hash("WHAT IS THE CAPITAL OF FRANCE?", user_id)
        assert h1 == h2 == h3

    def test_hash_user_isolation(self):
        """Same question from different users produces different hashes."""
        q = "What is the capital of France?"
        h1 = cache.question_hash(q, user_id=1)
        h2 = cache.question_hash(q, user_id=2)
        assert h1 != h2

    def test_hash_format(self):
        """Hash is a 64-character SHA-256 hex digest."""
        h = cache.question_hash("test question", user_id=1)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestGetCachedAnswer:
    """Test get_cached_answer() behavior."""

    def setup_method(self):
        """Clear the global cache before each test."""
        cache.clear_cache()

    def teardown_method(self):
        """Clear after each test."""
        cache.clear_cache()

    def test_get_cached_answer_returns_none_when_absent(self):
        """Returns None when no entry exists."""
        result = cache.get_cached_answer("never seen question", user_id=1)
        assert result is None

    def test_get_cached_answer_returns_stored_response(self):
        """Returns the stored response after set_cached_answer()."""
        question = "What is the capital of France?"
        user_id = 1
        response_data = {"answer": "Paris", "sources": ["https://example.com"]}

        cache.set_cached_answer(question, user_id, response_data)
        result = cache.get_cached_answer(question, user_id)

        assert result == response_data

    def test_get_cached_answer_user_isolation(self):
        """User A's cache entry is not visible to user B."""
        question = "What is the capital of France?"
        response_a = {"answer": "Paris", "user": "A"}
        response_b = {"answer": "Berlin", "user": "B"}

        cache.set_cached_answer(question, user_id=1, response=response_a)
        cache.set_cached_answer(question, user_id=2, response=response_b)

        assert cache.get_cached_answer(question, user_id=1) == response_a
        assert cache.get_cached_answer(question, user_id=2) == response_b

    def test_get_cached_answer_expired_entry_returns_none(self):
        """Returns None when TTL has expired."""
        question = "What is the capital of France?"
        user_id = 1
        response_data = {"answer": "Paris"}

        cache.set_cached_answer(question, user_id, response_data)

        # Manually advance expires_at past current time to simulate TTL expiry.
        key = cache.question_hash(question, user_id)
        cache._CACHE[key]["expires_at"] = time.time() - 1
        result = cache.get_cached_answer(question, user_id)
        assert result is None

    def test_get_cached_answer_within_ttl_returns_entry(self):
        """Returns the stored response when queried within TTL window."""
        question = "What is the capital of France?"
        user_id = 1
        response_data = {"answer": "Paris"}

        cache.set_cached_answer(question, user_id, response_data)

        # expires_at is already set to current_time + TTL_SECONDS; querying
        # within that window should still return the entry.
        result = cache.get_cached_answer(question, user_id)
        assert result == response_data


class TestSetCachedAnswer:
    """Test set_cached_answer() behavior."""

    def setup_method(self):
        cache.clear_cache()

    def teardown_method(self):
        cache.clear_cache()

    def test_set_cached_answer_stores_response(self):
        """Stores a response that can be retrieved."""
        question = "Explain RAG systems."
        user_id = 5
        response = {"answer": "Retrieval-Augmented Generation", "sources": []}

        cache.set_cached_answer(question, user_id, response)
        result = cache.get_cached_answer(question, user_id)

        assert result == response

    def test_set_cached_answer_overwrites_previous(self):
        """New response for the same question overwrites the old one."""
        question = "What is RAG?"
        user_id = 1

        cache.set_cached_answer(question, user_id, {"answer": "First"})
        cache.set_cached_answer(question, user_id, {"answer": "Second"})

        result = cache.get_cached_answer(question, user_id)
        assert result == {"answer": "Second"}


class TestClearCache:
    """Test clear_cache() behavior."""

    def test_clear_cache_removes_all_entries(self):
        """clear_cache() empties the entire cache."""
        cache.set_cached_answer("Q1", user_id=1, response={"a": 1})
        cache.set_cached_answer("Q2", user_id=2, response={"b": 2})

        cache.clear_cache()

        assert cache.get_cached_answer("Q1", user_id=1) is None
        assert cache.get_cached_answer("Q2", user_id=2) is None

    def test_clear_cache_on_empty_cache(self):
        """clear_cache() on an already-empty cache is a no-op."""
        cache.clear_cache()  # no error
        assert cache.get_cached_answer("Q", user_id=1) is None
