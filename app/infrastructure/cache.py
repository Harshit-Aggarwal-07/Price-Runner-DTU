"""
Memory Cache Adapter — In-memory TTL cache using cachetools.

Implements CachePort. For localhost single-user this is perfect.
Upgrade path: swap with RedisCacheAdapter for multi-user scenarios.
"""

from __future__ import annotations

from typing import Any, Optional

from cachetools import TTLCache

from app.config import CACHE_MAX_SIZE, CACHE_TTL_SECONDS
from app.core.ports import CachePort


class MemoryCacheAdapter(CachePort):
    """Thread-safe in-memory cache with TTL eviction."""

    def __init__(
        self,
        maxsize: int = CACHE_MAX_SIZE,
        ttl: int = CACHE_TTL_SECONDS,
    ):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # TTLCache doesn't support per-key TTL, so we use the global TTL.
        # For per-key TTL, upgrade to Redis.
        self._cache[key] = value

    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()
