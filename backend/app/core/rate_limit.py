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
    """Fixed-window rate limiter with Redis backing when available."""

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

    def __init__(self) -> None:
        self._local_attempts_by_key: dict[str, deque[datetime]] = defaultdict(deque)
        self._local_lock = Lock()
        self._redis_client: Optional[object] = None
        self._redis_script: Optional[object] = None

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
        fail_closed: bool = True,
    ) -> tuple[bool, int]:
        """Return whether a request should be limited and the retry-after value.

        When *fail_closed* is ``True`` (default) and the Redis call fails, the
        request is treated as rate-limited so the system does not serve traffic
        without protection.  Set *fail_closed* to ``False`` to fall back to an
        in-process tracking window (useful for local development / tests).
        """

        client = self._get_redis_client()
        if client is not None:
            try:
                return self._check_redis(client, key, limit, window_seconds, cost)
            except Exception:
                logger.exception("Redis rate limiting failed for %s.", key)
                if fail_closed:
                    return True, window_seconds

        return self._check_local(key, limit, window_seconds, cost)


guard_scan_rate_limiter = DistributedRateLimiter()