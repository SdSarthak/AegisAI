"""Shared rate limiting helpers."""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import logging
from threading import Lock
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis
except ImportError:  # pragma: no cover - exercised only when the dependency is missing
    redis = None


class DistributedRateLimiter:
    """Fixed-window rate limiter with Redis backing when available, featuring a circuit breaker."""

    _RATE_LIMIT_SCRIPT = """
local current = redis.call('INCRBY', KEYS[1], ARGV[1])
if current == tonumber(ARGV[1]) then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
  ttl = tonumber(ARGV[2])
end
return {current, ttl}
"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ) -> None:
        self._local_attempts_by_key: dict[str, deque[datetime]] = defaultdict(deque)
        self._local_lock = Lock()
        self._redis_client: Optional[object] = None
        self._redis_script: Optional[object] = None

        # Circuit breaker settings and state
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.cb_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.consecutive_failures = 0
        self.last_state_change: datetime = datetime.now(timezone.utc)

        # Health metrics
        self.metrics = {
            "total_requests": 0,
            "redis_calls": 0,
            "redis_failures": 0,
            "local_fallbacks": 0,
            "blocked_by_circuit_breaker": 0,
            "failures_closed": 0,
            "failures_open": 0,
        }

    def _get_redis_client(self) -> Optional[object]:
        if not settings.REDIS_URL or redis is None:
            return None

        if self._redis_client is None:
            self._redis_client = redis.Redis.from_url(  # type: ignore[union-attr]
                settings.REDIS_URL,
                decode_responses=True,
            )

        return self._redis_client

    def _check_redis(
        self,
        client: object,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int,
    ) -> tuple[bool, int]:
        if self._redis_script is None:
            self._redis_script = client.register_script(self._RATE_LIMIT_SCRIPT)  # type: ignore[attr-defined]

        current, ttl = self._redis_script(  # type: ignore[operator]
            keys=[key],
            args=[cost, window_seconds],
        )

        if int(current) > limit:
            retry_after = int(ttl) if int(ttl) > 0 else window_seconds
            return True, retry_after

        return False, 0

    def _check_local(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int,
    ) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        with self._local_lock:
            attempts = self._local_attempts_by_key[key]

            while attempts and attempts[0] <= window_start:
                attempts.popleft()

            if len(attempts) + cost > limit:
                retry_after = (
                    max(
                        1,
                        int(
                            (
                                window_seconds
                                - (now - attempts[0]).total_seconds()
                            )
                            + 0.999
                        ),
                    )
                    if attempts
                    else window_seconds
                )
                return True, retry_after

            for _ in range(cost):
                attempts.append(now)

            return False, 0

    def check_and_consume(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int = 1,
        fail_closed: Optional[bool] = None,
    ) -> tuple[bool, int]:
        """Return whether a request should be limited and the retry-after value."""
        if fail_closed is None:
            fail_closed = getattr(settings, "RATE_LIMIT_FAIL_CLOSED", False)

        now = datetime.now(timezone.utc)
        use_redis = False
        client = None

        with self._local_lock:
            self.metrics["total_requests"] += 1

            # Evaluate/Update Circuit Breaker State
            if self.cb_state == "OPEN":
                elapsed = (now - self.last_state_change).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.cb_state = "HALF_OPEN"
                    self.last_state_change = now
                    logger.warning("Circuit breaker transitioning from OPEN to HALF_OPEN for rate limiter.")
                    use_redis = True
                else:
                    self.metrics["blocked_by_circuit_breaker"] += 1
            else:
                use_redis = True

            if use_redis:
                client = self._get_redis_client()
                if client is None:
                    # Redis is not configured or available (local dev fallback)
                    use_redis = False

        # Redis operation block (executed outside local lock to prevent contention)
        if use_redis and client is not None:
            try:
                with self._local_lock:
                    self.metrics["redis_calls"] += 1

                limited, retry_after = self._check_redis(client, key, limit, window_seconds, cost)

                with self._local_lock:
                    if self.cb_state == "HALF_OPEN":
                        self.cb_state = "CLOSED"
                        self.consecutive_failures = 0
                        self.last_state_change = datetime.now(timezone.utc)
                        logger.info("Circuit breaker reset to CLOSED after successful Redis call.")
                    elif self.cb_state == "CLOSED":
                        self.consecutive_failures = 0

                return limited, retry_after

            except Exception:
                logger.exception("Redis rate limiting failed for %s", key)

                with self._local_lock:
                    self.metrics["redis_failures"] += 1
                    self.consecutive_failures += 1

                    if self.cb_state != "OPEN" and self.consecutive_failures >= self.failure_threshold:
                        self.cb_state = "OPEN"
                        self.last_state_change = datetime.now(timezone.utc)
                        logger.error(
                            "Circuit breaker tripped to OPEN state due to %d consecutive Redis failures.",
                            self.consecutive_failures,
                        )

                    if fail_closed:
                        self.metrics["failures_closed"] += 1
                        return True, window_seconds
                    else:
                        self.metrics["failures_open"] += 1

        # Fallback to Local Tracking
        with self._local_lock:
            self.metrics["local_fallbacks"] += 1

            # If Redis was configured and active, but we skipped it because the circuit breaker is OPEN,
            # we should fail closed if fail_closed is True.
            redis_configured = bool(settings.REDIS_URL and redis is not None)
            if redis_configured and self.cb_state == "OPEN" and fail_closed:
                self.metrics["failures_closed"] += 1
                return True, window_seconds

        return self._check_local(key, limit, window_seconds, cost)

    def clear(self) -> None:
        """Clear local rate-limit state for test isolation."""
        with self._local_lock:
            self._local_attempts_by_key.clear()

guard_scan_rate_limiter = DistributedRateLimiter()
badge_rate_limiter = DistributedRateLimiter()
