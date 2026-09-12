"""
Domain Ports — Abstract interfaces (ABCs) defining contracts.

These are the "ports" in Hexagonal Architecture.
The domain core depends ONLY on these abstractions.
Concrete implementations live in adapters/ and infrastructure/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.models import (
    DeliveryInfo,
    Location,
    NormalizedProduct,
    RawListing,
)


class PlatformPort(ABC):
    """
    Abstract interface for any grocery platform adapter.

    To add a new platform (e.g., Zepto), create a new class implementing
    this interface in app/adapters/. Register it in config.ENABLED_PLATFORMS.
    No other code changes required (Open/Closed Principle).
    """

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """Unique identifier, e.g., 'blinkit', 'instamart'."""
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable name, e.g., 'Blinkit', 'Swiggy Instamart'."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Platform's base URL, e.g., 'https://blinkit.com'."""
        ...

    @abstractmethod
    async def search(
        self, query: str, location: Location
    ) -> list[RawListing]:
        """
        Search for products matching the query at the given location.

        Returns a list of RawListing objects (platform-specific format).
        Must return an empty list (never None) if no results found.
        Must raise PlatformError subclasses on failure, never raw exceptions.
        """
        ...

    @abstractmethod
    async def get_delivery_info(self, location: Location) -> DeliveryInfo:
        """Get delivery cost information for the given location."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Quick check if the platform is reachable. Returns True if healthy."""
        ...

    def get_product_url(self, product_id: str) -> Optional[str]:
        """Build a deep-link URL for a specific product. Override if supported."""
        return None


class CachePort(ABC):
    """
    Abstract interface for caching search results.

    Implementations: MemoryCacheAdapter (default), RedisCacheAdapter (scale path).
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value. Returns None on miss."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with optional TTL in seconds."""
        ...

    @abstractmethod
    def size(self) -> int:
        """Return current number of cached entries."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached entries."""
        ...


class MatchingStrategy(ABC):
    """
    Abstract interface for product matching strategies.

    Implementations: ExactMatch, TokenSetRatio, Levenshtein, HybridGated.
    Each can be used independently or compared side-by-side (debug view).
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable name, e.g., 'Exact Match', 'Token Set Ratio'."""
        ...

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Machine identifier, e.g., 'exact', 'token_set'."""
        ...

    @abstractmethod
    def compute_similarity(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> float:
        """
        Compute similarity score between two normalized products.

        Returns a float between 0.0 (completely different) and 1.0 (identical).
        Must be deterministic: same inputs → same output.
        Must be symmetric: similarity(a, b) == similarity(b, a).
        """
        ...


# ═══════════════════════════════════════════════
#  DOMAIN EXCEPTIONS
# ═══════════════════════════════════════════════


class PlatformError(Exception):
    """Base exception for all platform-related errors."""

    def __init__(self, platform: str, message: str):
        self.platform = platform
        super().__init__(f"[{platform}] {message}")


class PlatformTimeoutError(PlatformError):
    """Platform didn't respond within timeout."""
    pass


class PlatformBlockedError(PlatformError):
    """Platform detected us as a bot or returned a challenge."""
    pass


class PlatformParseError(PlatformError):
    """Platform returned data we couldn't parse (schema changed)."""
    pass


class LocationNotServedError(PlatformError):
    """Platform doesn't deliver to this location."""
    pass
