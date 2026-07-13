"""Unit tests for the Redis-backed two-level RAG cache."""

import fnmatch
import time

from app.modules.rag.cache import CachedAnswer, SemanticCache


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expiry = {}
        self.sets = {}
        self.commands = []
        self.in_pipeline = False

    def pipeline(self):
        self.commands = []
        self.in_pipeline = True
        return self

    def execute(self):
        commands, self.commands = self.commands, []
        self.in_pipeline = False
        return [command() for command in commands]

    def setex(self, key, ttl, value):
        def operation():
            self.values[key] = value
            self.expiry[key] = time.time() + ttl
            return True
        if self.in_pipeline:
            self.commands.append(operation)
            return self
        operation()
        return True

    def get(self, key):
        if key in self.expiry and self.expiry[key] <= time.time():
            self.values.pop(key, None)
            self.expiry.pop(key, None)
        return self.values.get(key)

    def sadd(self, key, value):
        def operation():
            before = len(self.sets.setdefault(key, set()))
            self.sets[key].add(value)
            return len(self.sets[key]) - before
        if self.in_pipeline:
            self.commands.append(operation)
            return self
        return operation()

    def smembers(self, key):
        return self.sets.get(key, set()).copy()

    def srem(self, key, value):
        def operation():
            existed = value in self.sets.get(key, set())
            self.sets.get(key, set()).discard(value)
            return int(existed)
        if self.in_pipeline:
            self.commands.append(operation)
            return self
        return operation()

    def delete(self, *keys):
        def operation():
            deleted = 0
            for key in keys:
                deleted += int(key in self.values or key in self.sets)
                self.values.pop(key, None)
                self.expiry.pop(key, None)
                self.sets.pop(key, None)
            return deleted
        if self.in_pipeline:
            self.commands.append(operation)
            return self
        return operation()

    def scan_iter(self, match):
        return [key for key in self.values if fnmatch.fnmatch(key, match)]


def _answer():
    return CachedAnswer("Article 6 answer", [{"source": "act.pdf"}], 0.95, "HIGH")


def test_exact_hit_does_not_compute_embedding_twice():
    client = FakeRedis()
    calls = []
    cache = SemanticCache("", lambda q: calls.append(q) or [1.0, 0.0], client=client)
    cache.set("What does Article 6 require?", _answer())

    hit = cache.get("What does Article 6 require?")

    assert hit and hit.cache_type == "exact"
    assert calls == ["What does Article 6 require?"]


def test_semantic_hit_promotes_paraphrase_to_exact_cache():
    client = FakeRedis()
    embeddings = {
        "What does Article 6 say?": [1.0, 0.0],
        "Explain Article 6": [0.99, 0.01],
    }
    cache = SemanticCache("", embeddings.__getitem__, client=client)
    cache.set("What does Article 6 say?", _answer())

    first = cache.get("Explain Article 6")
    second = cache.get("Explain Article 6")

    assert first and first.cache_type == "semantic"
    assert second and second.cache_type == "exact"


def test_cache_miss_below_similarity_threshold():
    client = FakeRedis()
    embeddings = {"Article 6": [1.0, 0.0], "Annex III": [0.0, 1.0]}
    cache = SemanticCache("", embeddings.__getitem__, client=client)
    cache.set("Article 6", _answer())
    assert cache.get("Annex III") is None


def test_cache_entries_are_isolated_by_tenant_namespace():
    client = FakeRedis()
    cache = SemanticCache("", lambda _: [1.0, 0.0], client=client)
    cache.set("Article 6", _answer(), namespace="user:1")

    assert cache.get("Article 6", namespace="user:1") is not None
    assert cache.get("Article 6", namespace="user:2") is None


def test_per_question_and_full_invalidation():
    client = FakeRedis()
    cache = SemanticCache("", lambda _: [1.0, 0.0], client=client)
    cache.set("Article 6", _answer())
    digest = cache.question_hash("Article 6")
    assert cache.invalidate(digest) == 2
    assert cache.get("Article 6") is None

    cache.set("Article 6", _answer())
    assert cache.invalidate_all() >= 2
    assert cache.get("Article 6") is None


def test_ttl_expiry_removes_cached_answer(monkeypatch):
    now = 1_000.0
    monkeypatch.setattr(time, "time", lambda: now)
    client = FakeRedis()
    cache = SemanticCache("", lambda _: [1.0], ttl_seconds=10, client=client)
    cache.set("Article 6", _answer())
    now = 1_011.0
    assert cache.get("Article 6") is None
