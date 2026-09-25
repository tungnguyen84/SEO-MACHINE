"""
Production Sliding-Window Rate Limiting Engine
Defends against endpoint abuse, brute force attacks, and runaway external API calls (LLM / SERP / Sandbox).
Emits standard HTTP 429 Too Many Requests with Retry-After header.
"""

import time
import threading
from typing import Dict, List, Tuple, Optional
from fastapi import HTTPException, Request, Response


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60, detail: str = "Rate limit exceeded. Please retry later."):
        super().__init__(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(retry_after)}
        )


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding-window rate limiter.
    Maintains timestamp logs per client/tenant key within a rolling window.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._events: Dict[str, List[float]] = {}

    def check_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Evaluates whether a request with the given key is within the rate limit.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            history = self._events.setdefault(key, [])
            # Prune events older than the sliding window
            self._events[key] = [ts for ts in history if ts > cutoff]
            valid_history = self._events[key]

            if len(valid_history) >= max_requests:
                # Oldest event in window determines when slot frees up
                oldest_event = valid_history[0]
                retry_after = max(1, int(oldest_event + window_seconds - now))
                return False, retry_after

            # Register current request
            self._events[key].append(now)
            return True, 0

    def enforce(self, key: str, max_requests: int, window_seconds: int = 60, resource_name: str = "API"):
        """Enforces rate limit, raising RateLimitExceeded (HTTP 429) if exceeded."""
        allowed, retry_after = self.check_limit(key, max_requests, window_seconds)
        if not allowed:
            raise RateLimitExceeded(
                retry_after=retry_after,
                detail=f"{resource_name} rate limit exceeded ({max_requests} requests per {window_seconds}s). Retry in {retry_after}s."
            )

    def reset(self, key: Optional[str] = None):
        """Clears rate limit state (for test isolation)."""
        with self._lock:
            if key:
                self._events.pop(key, None)
            else:
                self._events.clear()


# Global singletons for standard tiers
global_api_limiter = SlidingWindowRateLimiter()
llm_call_limiter = SlidingWindowRateLimiter()
serp_call_limiter = SlidingWindowRateLimiter()
sandbox_limiter = SlidingWindowRateLimiter()


def rate_limit_endpoint(max_requests: int = 60, window_seconds: int = 60):
    """FastAPI dependency for endpoint-level rate limiting."""
    def dependency(request: Request):
        # Identify by IP or client host
        client_ip = request.client.host if request.client else "127.0.0.1"
        endpoint = request.url.path
        key = f"ep:{client_ip}:{endpoint}"
        global_api_limiter.enforce(key, max_requests, window_seconds, resource_name=f"Endpoint {endpoint}")
    return dependency
