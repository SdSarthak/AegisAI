import time

from app.modules.rag.cache import (
    clear_cache,
    get_cached_answer,
    question_hash,
    set_cached_answer,
)


def test_cache_returns_none_on_miss():
    clear_cache()

    assert get_cached_answer("What is Article 6?") is None


def test_cache_returns_answer_for_exact_question():
    clear_cache()
    response = {
        "answer": "Article 6 defines high-risk classification.",
        "sources": [{"source": "eu-ai-act.pdf"}],
    }

    set_cached_answer("What is Article 6?", response)

    assert get_cached_answer("What is Article 6?") == response


def test_cache_normalizes_question_before_hashing():
    assert question_hash(" What   Is Article 6? ") == question_hash(
        "what is article 6?"
    )


def test_cache_expires(monkeypatch):
    clear_cache()
    now = 1000.0

    monkeypatch.setattr(time, "time", lambda: now)
    set_cached_answer("What is Article 6?", {"answer": "cached"})

    monkeypatch.setattr(time, "time", lambda: now + 301)

    assert get_cached_answer("What is Article 6?") is None
