"""Unit tests for the shared rate limiter helper."""

from types import SimpleNamespace

from app.core import rate_limit
from app.core.config import settings


class _FakeScript:
    def __init__(self, store: dict[str, int]):
        self._store = store

    def __call__(self, keys, args):
        key = keys[0]
        cost = int(args[0])
        window_seconds = int(args[1])

        current = self._store.get(key, 0) + cost
        self._store[key] = current
        ttl = window_seconds
        return current, ttl


class _FakeRedisClient:
    def __init__(self):
        self.store: dict[str, int] = {}

    def register_script(self, script):
        return _FakeScript(self.store)


class _FakeRedisModule:
    def __init__(self, client: _FakeRedisClient):
        self._client = client
        self.Redis = SimpleNamespace(from_url=self._from_url)

    def _from_url(self, *args, **kwargs):
        return self._client


def test_distributed_rate_limiter_uses_redis_backing(monkeypatch):
    """When Redis is configured, the limiter increments a shared key."""

    fake_client = _FakeRedisClient()
    fake_module = _FakeRedisModule(fake_client)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(rate_limit, "redis", fake_module)

    limiter = rate_limit.DistributedRateLimiter()

    for _ in range(60):
        limited, retry_after = limiter.check_and_consume(
            key="guard:scan:1",
            limit=60,
            window_seconds=60,
        )

        assert limited is False
        assert retry_after == 0

    limited, retry_after = limiter.check_and_consume(
        key="guard:scan:1",
        limit=60,
        window_seconds=60,
    )

    assert limited is True
    assert retry_after == 60
