"""
Search API — GET /api/search endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.models import MatchResult

router = APIRouter(prefix="/api", tags=["Search"])

# These will be set during app startup via dependency injection
_orchestrator = None
_location = None


def init_search_api(orchestrator, location):
    """Called during startup to inject dependencies."""
    global _orchestrator, _location
    _orchestrator = orchestrator
    _location = location


@router.get("/search", response_model=MatchResult)
async def search_products(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    strategy: str = Query("hybrid", description="Matching strategy: exact, token_set, levenshtein, hybrid"),
    debug: bool = Query(False, description="Include all strategy scores in response"),
):
    """
    Search for products across all platforms and return matched comparisons.

    - **q**: The product to search for (e.g., "maggi", "milk", "bread")
    - **strategy**: Which matching algorithm to use (default: hybrid)
    - **debug**: If true, includes scores from ALL strategies for each match
    """
    result = await _orchestrator.search(
        query=q.strip(),
        location=_location,
        strategy=strategy,
        include_all_strategies=debug,
    )
    return result
