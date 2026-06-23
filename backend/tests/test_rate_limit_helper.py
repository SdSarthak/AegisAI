"""Unit tests for the shared rate limiter helper."""

from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

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


class _FailingRedisClient:
    def register_script(self, script):
        raise Exception("Redis connection refused")


def test_distributed_rate_limiter_fail_open(monkeypatch):
    """When Redis fails and fail_closed is False, we fallback to local tracking (fail open)."""
    fake_client = _FailingRedisClient()
    fake_module = _FakeRedisModule(fake_client)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(rate_limit, "redis", fake_module)

    limiter = rate_limit.DistributedRateLimiter(failure_threshold=5)

    # 1. First call fails and falls back to local tracking
    limited, retry_after = limiter.check_and_consume(
        key="test:fail_open",
        limit=2,
        window_seconds=60,
        fail_closed=False,
    )
    assert limited is False
    assert retry_after == 0
    assert limiter.metrics["redis_failures"] == 1
    assert limiter.metrics["local_fallbacks"] == 1
    assert limiter.metrics["failures_open"] == 1
    assert limiter.metrics["failures_closed"] == 0

    # 2. Consume quota locally
    limited, retry_after = limiter.check_and_consume(
        key="test:fail_open",
        limit=2,
        window_seconds=60,
        fail_closed=False,
    )
    assert limited is False

    # 3. Third call should be limited locally
    limited, retry_after = limiter.check_and_consume(
        key="test:fail_open",
        limit=2,
        window_seconds=60,
        fail_closed=False,
    )
    assert limited is True
    assert retry_after > 0


def test_distributed_rate_limiter_fail_closed(monkeypatch):
    """When Redis fails and fail_closed is True, we fail closed (block request)."""
    fake_client = _FailingRedisClient()
    fake_module = _FakeRedisModule(fake_client)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(rate_limit, "redis", fake_module)

    limiter = rate_limit.DistributedRateLimiter(failure_threshold=5)

    limited, retry_after = limiter.check_and_consume(
        key="test:fail_closed",
        limit=10,
        window_seconds=60,
        fail_closed=True,
    )
    assert limited is True
    assert retry_after == 60
    assert limiter.metrics["redis_failures"] == 1
    assert limiter.metrics["failures_closed"] == 1
    assert limiter.metrics["failures_open"] == 0


def test_distributed_rate_limiter_circuit_breaker_trips(monkeypatch):
    """Circuit breaker transitions to OPEN after threshold consecutive failures."""
    fake_client = _FailingRedisClient()
    fake_module = _FakeRedisModule(fake_client)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(rate_limit, "redis", fake_module)

    # Use threshold of 2
    limiter = rate_limit.DistributedRateLimiter(failure_threshold=2, recovery_timeout=30)

    # State is initially CLOSED
    assert limiter.cb_state == "CLOSED"

    # First failure
    limiter.check_and_consume("key", 10, 60, fail_closed=False)
    assert limiter.cb_state == "CLOSED"
    assert limiter.consecutive_failures == 1

    # Second failure -> should trip circuit breaker to OPEN
    limiter.check_and_consume("key", 10, 60, fail_closed=False)
    assert limiter.cb_state == "OPEN"
    assert limiter.consecutive_failures == 2

    # Third call: circuit breaker is OPEN, so Redis is not called
    limited, retry_after = limiter.check_and_consume("key", 10, 60, fail_closed=False)
    assert limiter.metrics["blocked_by_circuit_breaker"] == 1
    assert limiter.metrics["redis_failures"] == 2  # Has not increased!


def test_distributed_rate_limiter_circuit_breaker_recovery(monkeypatch):
    """Circuit breaker recovers (transitions to HALF-OPEN then CLOSED) after recovery timeout."""
    fake_client = _FakeRedisClient()
    fake_module = _FakeRedisModule(fake_client)

    # Initially use failing client to trip the circuit breaker
    failing_client = _FailingRedisClient()
    failing_module = _FakeRedisModule(failing_client)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(rate_limit, "redis", failing_module)

    # Set recovery_timeout to 0 for instant recovery in tests
    limiter = rate_limit.DistributedRateLimiter(failure_threshold=1, recovery_timeout=0)

    # 1. Trigger failure -> CB trips to OPEN
    limiter.check_and_consume("key", 10, 60, fail_closed=False)
    assert limiter.cb_state == "OPEN"

    # 2. Switch to working Redis module to simulate recovery
    monkeypatch.setattr(rate_limit, "redis", fake_module)
    limiter._redis_client = None  # Reset cached client

    # 3. Next call should transition from OPEN to HALF_OPEN, attempt Redis, succeed, and transition back to CLOSED
    limited, retry_after = limiter.check_and_consume("key", 10, 60, fail_closed=False)
    assert limited is False
    assert limiter.cb_state == "CLOSED"
    assert limiter.consecutive_failures == 0


def test_distributed_rate_limiter_cleans_up_stale_local_keys(monkeypatch):
    """Expired in-memory keys are removed during the periodic cleanup sweep.

    With the fix, _check_local runs cleanup before the rate-limit check on every
    invocation (not only on non-rate-limited calls). This means:
    1. The stale entry from the first call is removed during the second call
       (before the rate-limit check evaluates).
    2. cleanup_stale_local_attempts() called afterwards finds nothing stale.
    """
    fake_now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        current = fake_now

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(rate_limit, "datetime", FrozenDateTime)

    limiter = rate_limit.DistributedRateLimiter(cleanup_interval=1)
    # First call: records "now" in the deque for stale:key
    limited, retry_after = limiter.check_and_consume(
        key="stale:key",
        limit=1,
        window_seconds=60,
        fail_closed=False,
    )
    assert limited is False
    assert retry_after == 0
    # Cleanup ran during _check_local (cleanup_interval=1), counter reset to 0
    assert limiter.cleanup_stale_local_attempts() == 0

    # Advance time past the window
    FrozenDateTime.current = fake_now + timedelta(seconds=61)

    # Second call: cleanup runs BEFORE rate-limit check, removes the stale entry
    # (the entry from first call is now outside the 60-second window).
    # Since the deque is empty after cleanup, rate-limit check evaluates:
    #   len([]) + 1 > 1  =>  False  => not rate-limited
    limited2, _ = limiter.check_and_consume(
        key="stale:key",
        limit=1,
        window_seconds=60,
        fail_closed=False,
    )
    assert limited2 is False  # Not rate-limited because stale entry was cleaned first
    assert limiter.cleanup_stale_local_attempts() == 0  # Nothing left to clean
