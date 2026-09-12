"""
Health API — GET /api/health endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.models import HealthResponse, PlatformHealth

router = APIRouter(prefix="/api", tags=["Health"])

_registry = None
_cache = None


def init_health_api(registry, cache):
    """Called during startup to inject dependencies."""
    global _registry, _cache
    _registry = registry
    _cache = cache


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of all registered platform adapters and cache.
    """
    platform_health: dict[str, PlatformHealth] = {}

    if _registry:
        for adapter in _registry.get_all_adapters():
            try:
                healthy = await adapter.health_check()
                platform_health[adapter.platform_id] = PlatformHealth(
                    status="up" if healthy else "down",
                )
            except Exception:
                platform_health[adapter.platform_id] = PlatformHealth(
                    status="down",
                )

    return HealthResponse(
        status="healthy",
        platforms=platform_health,
        cache_size=_cache.size() if _cache else 0,
    )
