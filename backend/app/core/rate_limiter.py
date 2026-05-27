"""Rate limiting module for per-user request throttling."""

from time import time
from collections import defaultdict
from typing import Dict, Tuple


class RateLimiter:
    """Per-user rate limiter with sliding window tracking."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._cache: Dict[str, list] = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        """
        Check if a user is allowed to make a request.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time()
        cutoff = now - self.window_seconds
        
        # Remove expired timestamps
        if user_id in self._cache:
            self._cache[user_id] = [ts for ts in self._cache[user_id] if ts > cutoff]
        
        # Check if user has exceeded limit
        if len(self._cache[user_id]) >= self.max_requests:
            return False
        
        # Record this request
        self._cache[user_id].append(now)
        return True

    def get_retry_after(self, user_id: str) -> int:
        """
        Get seconds until the user can retry.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Seconds to wait before retrying
        """
        if user_id not in self._cache or not self._cache[user_id]:
            return 0
        
        oldest_request = self._cache[user_id][0]
        retry_after = int(oldest_request + self.window_seconds - time()) + 1
        return max(retry_after, 1)

    def clear(self):
        """Clear all tracking data."""
        self._cache.clear()


# Global rate limiter instance: 60 requests per 60 seconds
limiter = RateLimiter(max_requests=60, window_seconds=60)
