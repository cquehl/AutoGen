"""
MCP Utility Functions

Provides helper utilities for MCP operations:
- Rate limiting
- Retry logic
- Cache management
- Resource monitoring
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import threading
import logging

from .errors import MCPRateLimitError, MCPError


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.

    Tracks requests per identifier (e.g., agent name) and enforces
    maximum requests within a time window.

    Example:
        >>> limiter = RateLimiter(max_requests=100, window_seconds=60)
        >>> limiter.check_limit("agent_1")  # True if within limit
        >>> limiter.record_request("agent_1")  # Record a request
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # Track timestamps of requests per identifier
        self._requests: Dict[str, List[float]] = defaultdict(list)

        # Thread safety
        self._lock = threading.RLock()

        logger.debug(
            f"Rate limiter initialized: {max_requests} requests per {window_seconds}s"
        )

    def check_limit(self, identifier: str) -> bool:
        """
        Check if identifier is within rate limit.

        Args:
            identifier: Unique identifier (e.g., agent name)

        Returns:
            True if within limit, False if exceeded
        """
        with self._lock:
            self._cleanup_old_requests(identifier)
            current_count = len(self._requests[identifier])
            return current_count < self.max_requests

    def record_request(self, identifier: str) -> None:
        """
        Record a request for identifier.

        Args:
            identifier: Unique identifier

        Raises:
            MCPRateLimitError: If rate limit exceeded
        """
        with self._lock:
            self._cleanup_old_requests(identifier)

            current_count = len(self._requests[identifier])
            if current_count >= self.max_requests:
                raise MCPRateLimitError(
                    message=f"Rate limit exceeded for {identifier}",
                    agent_name=identifier,
                    limit=self.max_requests,
                    window_seconds=self.window_seconds
                )

            # Record timestamp
            self._requests[identifier].append(time.time())

            logger.debug(
                f"Request recorded for {identifier}: "
                f"{current_count + 1}/{self.max_requests}"
            )

    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests in current window.

        Args:
            identifier: Unique identifier

        Returns:
            Number of requests remaining
        """
        with self._lock:
            self._cleanup_old_requests(identifier)
            current_count = len(self._requests[identifier])
            return max(0, self.max_requests - current_count)

    def reset(self, identifier: str) -> None:
        """
        Reset rate limit for identifier.

        Args:
            identifier: Unique identifier
        """
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]
                logger.debug(f"Rate limit reset for {identifier}")

    def _cleanup_old_requests(self, identifier: str) -> None:
        """Remove requests outside the time window"""
        now = time.time()
        cutoff = now - self.window_seconds

        if identifier in self._requests:
            # Keep only requests within window
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > cutoff
            ]

            # Clean up if empty
            if not self._requests[identifier]:
                del self._requests[identifier]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats per identifier
        """
        with self._lock:
            stats = {}
            for identifier in self._requests.keys():
                self._cleanup_old_requests(identifier)
                stats[identifier] = {
                    "current_count": len(self._requests[identifier]),
                    "remaining": self.get_remaining(identifier),
                    "limit": self.max_requests,
                    "window_seconds": self.window_seconds
                }
            return stats


class RetryHelper:
    """
    Helper for implementing retry logic with exponential backoff.

    Example:
        >>> async def flaky_operation():
        ...     # Might fail occasionally
        ...     ...
        >>> retry = RetryHelper(max_attempts=3, backoff_base=2.0)
        >>> result = await retry.execute(flaky_operation)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
        max_backoff: float = 30.0
    ):
        """
        Initialize retry helper.

        Args:
            max_attempts: Maximum retry attempts
            backoff_base: Base for exponential backoff
            max_backoff: Maximum backoff time in seconds
        """
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.max_backoff = max_backoff

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            Exception: Last exception if all retries failed
        """
        last_error = None

        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_attempts} failed: {e}"
                )

                # Don't sleep after last attempt
                if attempt < self.max_attempts - 1:
                    backoff = min(
                        self.backoff_base ** attempt,
                        self.max_backoff
                    )
                    logger.info(f"Retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)

        # All retries failed
        raise last_error or MCPError("All retry attempts failed")


class CacheManager:
    """
    Simple TTL-based cache manager.

    Example:
        >>> cache = CacheManager(ttl_seconds=300)
        >>> cache.set("key", {"data": "value"})
        >>> value = cache.get("key")  # Returns {"data": "value"}
        >>> # After TTL expires
        >>> value = cache.get("key")  # Returns None
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache manager.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.RLock()

        logger.debug(f"Cache initialized: TTL={ttl_seconds}s, max_size={max_size}")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        with self._lock:
            if key not in self._cache:
                return None

            # Check TTL
            if self._is_expired(key):
                self._remove(key)
                return None

            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()

            self._cache[key] = value
            self._timestamps[key] = datetime.utcnow()

    def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry.

        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            self._remove(key)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            logger.debug("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key in self._cache.keys()
                if self._is_expired(key)
            ]

            for key in expired_keys:
                self._remove(key)

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "oldest_entry_age": self._get_oldest_age()
            }

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self._timestamps:
            return True

        age = datetime.utcnow() - self._timestamps[key]
        return age.total_seconds() > self.ttl_seconds

    def _remove(self, key: str) -> None:
        """Remove entry from cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry"""
        if not self._timestamps:
            return

        oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
        self._remove(oldest_key)
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")

    def _get_oldest_age(self) -> Optional[float]:
        """Get age of oldest entry in seconds"""
        if not self._timestamps:
            return None

        oldest_time = min(self._timestamps.values())
        age = datetime.utcnow() - oldest_time
        return age.total_seconds()


async def schedule_periodic_task(
    func: Callable,
    interval_seconds: float,
    task_name: str = "periodic_task"
) -> asyncio.Task:
    """
    Schedule a periodic task to run at specified interval.

    Args:
        func: Async function to run periodically
        interval_seconds: Interval between runs in seconds
        task_name: Name for the task (for logging)

    Returns:
        Async task handle

    Example:
        >>> async def cleanup():
        ...     print("Cleaning up...")
        >>> task = await schedule_periodic_task(cleanup, 60, "cleanup")
        >>> # Later: task.cancel()
    """
    async def run_periodic():
        logger.info(f"Starting periodic task: {task_name}")
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await func()
                except Exception as e:
                    logger.error(f"Periodic task {task_name} failed: {e}")
        except asyncio.CancelledError:
            logger.info(f"Periodic task {task_name} cancelled")

    task = asyncio.create_task(run_periodic(), name=task_name)
    return task
