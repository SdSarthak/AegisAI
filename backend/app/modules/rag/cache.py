"""Lightweight in-memory cache for repeated RAG queries."""

import hashlib
import time
from typing import Any

_CACHE: dict[str, dict[str, Any]] = {}
TTL_SECONDS = 300


def normalize_question(question: str) -> str:
    return " ".join(question.lower().strip().split())


def question_hash(question: str, user_id: int) -> str:
    normalized = normalize_question(question)
    return hashlib.sha256(f"{user_id}:{normalized}".encode("utf-8")).hexdigest()


def get_cached_answer(question: str, user_id: int) -> dict[str, Any] | None:
    key = question_hash(question, user_id)
    cached = _CACHE.get(key)

    if not cached:
        return None

    if time.time() > cached["expires_at"]:
        _CACHE.pop(key, None)
        return None

    return cached["response"]


def set_cached_answer(question: str, user_id: int, response: dict[str, Any]) -> None:
    key = question_hash(question, user_id)
    _CACHE[key] = {
        "response": response,
        "expires_at": time.time() + TTL_SECONDS,
    }


def clear_cache() -> None:
    _CACHE.clear()