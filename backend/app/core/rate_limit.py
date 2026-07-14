"""Shared rate limiting helpers."""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import logging
from threading import Event, Lock
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis
except ImportError:  # pragma: no cover - exercised only when the dependency is missing
    redis = None

_REDIS_CONNECT_TIMEOUT = 2
_REDIS_OPERATION_TIMEOUT = 2


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
        cleanup_interval: int = 100,
    ) -> None:
        self._local_attempts_by_key: dict[str, deque[datetime]] = defaultdict(deque)
        self._local_window_seconds_by_key: dict[str, int] = {}
        self._local_lock = Lock()
        self._local_cleanup_interval = max(1, cleanup_interval)
        self._local_cleanup_calls = 0
        self._redis_client: Optional[object] = None
        self._redis_script: Optional[object] = None
        self._redis_init_lock = Lock()

        # Circuit breaker settings and state
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.cb_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.cb_event = Event()
        self.cb_event.set()  # CLOSED = set
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

        # Pre-warm Redis client if URL is configured
        if settings.REDIS_URL and redis is not None:
            self._redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
                socket_timeout=_REDIS_OPERATION_TIMEOUT,
            )

    def clear_local_attempts(self) -> None:
        """Clear the in-memory fallback state used when Redis is unavailable."""
        with self._local_lock:
            self._local_attempts_by_key.clear()
            self._local_window_seconds_by_key.clear()
            self._local_cleanup_calls = 0

    def cleanup_stale_local_attempts(self, now: Optional[datetime] = None) -> int:
        """Prune expired in-memory keys and return how many were removed."""
        with self._local_lock:
            return self._cleanup_stale_local_attempts_locked(now=now)

    def _cleanup_stale_local_attempts_locked(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        removed_keys = 0

        for key, attempts in list(self._local_attempts_by_key.items()):
            window_seconds = self._local_window_seconds_by_key.get(key)
            if window_seconds is None:
                window_seconds = 0

            cutoff = now - timedelta(seconds=window_seconds)
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()

            if not attempts:
                self._local_attempts_by_key.pop(key, None)
                self._local_window_seconds_by_key.pop(key, None)
                removed_keys += 1

        return removed_keys

    def _get_redis_client(self) -> Optional[object]:
        if not settings.REDIS_URL or redis is None:
            return None

        if self._redis_client is not None:
            return self._redis_client

        with self._redis_init_lock:
            if self._redis_client is None:
                self._redis_client = redis.Redis.from_url(  # type: ignore[union-attr]
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
                    socket_timeout=_REDIS_OPERATION_TIMEOUT,
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
            with self._redis_init_lock:
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
            existing_window = self._local_window_seconds_by_key.get(key, 0)
            if window_seconds > existing_window:
                self._local_window_seconds_by_key[key] = window_seconds

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

            self._local_cleanup_calls += 1
            if self._local_cleanup_calls >= self._local_cleanup_interval:
                self._local_cleanup_calls = 0
                self._cleanup_stale_local_attempts_locked(now=now)

            return False, 0

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        fail_closed: Optional[bool] = None,
    ) -> tuple[bool, int]:
        """Check whether a key is currently over the rate limit without consuming a slot."""
        return self._check_internal(key, limit, window_seconds, cost=0, fail_closed=fail_closed)

    def record_attempt(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        fail_closed: Optional[bool] = None,
    ) -> tuple[bool, int]:
        """Record one failed attempt, consuming one slot from the rate limit."""
        return self._check_internal(key, limit, window_seconds, cost=1, fail_closed=fail_closed)

    def _check_internal(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int,
        fail_closed: Optional[bool] = None,
    ) -> tuple[bool, int]:

        if fail_closed is None:
            fail_closed = getattr(settings, "RATE_LIMIT_FAIL_CLOSED", True)

        now = datetime.now(timezone.utc)
        use_redis = False

        # Evaluate/Update Circuit Breaker State (outside local lock to prevent contention)
        if self.cb_state == "OPEN":
            elapsed = (now - self.last_state_change).total_seconds()
            if elapsed >= self.recovery_timeout:
                self.cb_state = "HALF_OPEN"
                self.last_state_change = now
                logger.warning("Circuit breaker transitioning from OPEN to HALF_OPEN for rate limiter.")
                use_redis = True
            else:
                with self._local_lock:
                    self.metrics["blocked_by_circuit_breaker"] += 1
        else:
            use_redis = True

        # Get Redis client outside the local lock to avoid blocking all threads
        client = self._get_redis_client() if use_redis else None
        if client is None:
            use_redis = False

        # Redis operation block (executed outside local lock to prevent contention)
        if use_redis and client is not None:
            try:
                with self._local_lock:
                    self.metrics["total_requests"] += 1
                    self.metrics["redis_calls"] += 1

                limited, retry_after = self._check_redis(client, key, limit, window_seconds, cost)

                with self._local_lock:
                    if self.cb_state == "HALF_OPEN":
                        self.cb_state = "CLOSED"
                        self.cb_event.set()
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
                    self.metrics["total_requests"] += 1
                    self.consecutive_failures += 1

                    if self.cb_state != "OPEN" and self.consecutive_failures >= self.failure_threshold:
                        self.cb_state = "OPEN"
                        self.cb_event.clear()
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
            self.metrics["total_requests"] += 1
            self.metrics["local_fallbacks"] += 1

            # If Redis was configured and active, but we skipped it because the circuit breaker is OPEN,
            # we should fail closed if fail_closed is True.
            redis_configured = bool(settings.REDIS_URL and redis is not None)
            if redis_configured and self.cb_state == "OPEN" and fail_closed:
                self.metrics["failures_closed"] += 1
                return True, window_seconds

        return self._check_local(key, limit, window_seconds, cost)
    def check_and_consume(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int = 1,
        fail_closed: Optional[bool] = None,
    ) -> tuple[bool, int]:
        """Return whether a request should be limited and the retry-after value."""
        return self._check_internal(key, limit, window_seconds, cost=cost, fail_closed=fail_closed)





guard_scan_rate_limiter = DistributedRateLimiter()
badge_rate_limiter = DistributedRateLimiter()
