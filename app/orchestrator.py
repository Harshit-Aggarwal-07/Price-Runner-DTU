"""
Orchestrator — Coordinates the search pipeline.

Dispatches search queries to all registered platform adapters in parallel,
normalizes results, runs matching, and caches the output.
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.matcher import match_products
from app.core.models import Location, MatchResult, NormalizedProduct, SearchMetadata
from app.core.normalizer import normalize
from app.core.ports import CachePort, PlatformPort

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Coordinates fetch → normalize → match pipeline.
    
    Dependencies are injected (DIP): adapters and cache are passed in,
    not constructed internally.
    """

    def __init__(
        self,
        adapters: list[PlatformPort],
        cache: CachePort,
    ) -> None:
        self._adapters = adapters
        self._cache = cache

    async def search(
        self,
        query: str,
        location: Location,
        strategy: str = "hybrid",
        include_all_strategies: bool = False,
    ) -> MatchResult:
        """
        Execute a search across all platforms.

        1. Check cache
        2. Dispatch to all adapters in parallel
        3. Normalize results
        4. Match products across platforms
        5. Cache and return
        """
        cache_key = f"{query.lower().strip()}_{location.pincode}_{strategy}"

        # ── Check Cache ──
        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, MatchResult):
            logger.info(f"Cache hit for: {cache_key}")
            cached.metadata.cache_hit = True
            return cached

        logger.info(f"Cache miss for: {cache_key}. Fetching from {len(self._adapters)} platforms.")

        # ── Parallel Dispatch ──
        start = time.monotonic()

        # Use asyncio.gather with return_exceptions=True for failure isolation
        tasks = [
            self._fetch_and_normalize(adapter, query, location)
            for adapter in self._adapters
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = round(time.monotonic() - start, 3)

        # ── Collect Results & Metadata ──
        platform_products: dict[str, list[NormalizedProduct]] = {}
        fetch_times: dict[str, float] = {}
        platforms_available: list[str] = []
        platforms_failed: list[str] = []

        for adapter, result in zip(self._adapters, results):
            pid = adapter.platform_id
            if isinstance(result, Exception):
                logger.error(f"Platform {pid} failed: {result}")
                platforms_failed.append(pid)
            elif isinstance(result, tuple):
                products, fetch_time = result
                platform_products[pid] = products
                fetch_times[pid] = fetch_time
                platforms_available.append(pid)
                logger.info(f"Platform {pid}: {len(products)} products in {fetch_time:.2f}s")
            else:
                platforms_failed.append(pid)

        metadata = SearchMetadata(
            cache_hit=False,
            fetch_times=fetch_times,
            total_time=total_time,
            platforms_available=platforms_available,
            platforms_failed=platforms_failed,
        )

        # ── Match Products ──
        # Get products from each platform (handle 0, 1, or 2 platforms)
        platform_ids = list(platform_products.keys())

        if len(platform_ids) >= 2:
            # Normal case: match products across two platforms
            match_result = match_products(
                platform_a_products=platform_products[platform_ids[0]],
                platform_b_products=platform_products[platform_ids[1]],
                strategy=strategy,
                include_all_strategies=include_all_strategies,
                query=query,
                location=location,
                metadata=metadata,
            )
        elif len(platform_ids) == 1:
            # Only one platform available — no matching possible
            pid = platform_ids[0]
            match_result = MatchResult(
                query=query,
                location=location,
                matched_pairs=[],
                unmatched={pid: platform_products[pid]},
                metadata=metadata,
            )
        else:
            # Both platforms failed
            match_result = MatchResult(
                query=query,
                location=location,
                matched_pairs=[],
                unmatched={},
                metadata=metadata,
            )

        # ── Cache Result ──
        # Only cache when no platforms failed and we have valid results
        if not platforms_failed and match_result.matched_pairs:
            self._cache.set(cache_key, match_result)

        return match_result

    async def _fetch_and_normalize(
        self,
        adapter: PlatformPort,
        query: str,
        location: Location,
    ) -> tuple[list[NormalizedProduct], float]:
        """Fetch from one adapter and normalize results."""
        start = time.monotonic()

        raw_listings = await adapter.search(query, location)
        fetch_time = round(time.monotonic() - start, 3)

        # Normalize each listing
        normalized = [normalize(raw) for raw in raw_listings]

        return normalized, fetch_time
