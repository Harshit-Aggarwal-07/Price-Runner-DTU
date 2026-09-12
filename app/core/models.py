"""
Domain Models — All Pydantic models and value objects.

This module contains every data structure used across the application.
No external dependencies beyond pydantic. This IS the data contract.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════
#  VALUE OBJECTS (Immutable domain primitives)
# ═══════════════════════════════════════════════


class Location(BaseModel):
    """Geographic location for delivery area targeting."""

    latitude: float
    longitude: float
    label: str = "DTU Campus"
    pincode: str = "110042"


class WeightInfo(BaseModel):
    """Structured weight/volume extracted from a product name."""

    value: float              # 70
    unit: str                 # "g"
    base_value_grams: float   # Normalized to grams (or ml). 0.5 kg → 500.0
    base_unit: str            # "g" or "ml" or "units"
    raw_text: str             # Original extracted text, e.g., "70 g"
    is_multipack: bool = False
    pack_count: int = 1       # 4 for "Pack of 4 x 70g"

    def is_compatible(self, other: WeightInfo, tolerance_pct: float = 5.0) -> bool:
        """Check if two weights are within tolerance (for matching gate)."""
        if self.base_unit != other.base_unit:
            return False
        if self.base_value_grams == 0 or other.base_value_grams == 0:
            return False
        ratio = self.base_value_grams / other.base_value_grams
        return (1 - tolerance_pct / 100) <= ratio <= (1 + tolerance_pct / 100)


class ConfidenceLevel(str, Enum):
    """Human-readable confidence label for product matches."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NONE = "No Match"


# ═══════════════════════════════════════════════
#  ENTITIES (Core domain objects)
# ═══════════════════════════════════════════════


class RawListing(BaseModel):
    """
    Raw product data as scraped from a platform.
    Platform-specific, pre-normalization.
    """

    platform: str
    name: str
    price: float
    mrp: Optional[float] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    in_stock: bool = True
    rating: Optional[float] = None
    rating_count: Optional[str] = None
    raw_weight_text: Optional[str] = None
    category: Optional[str] = None
    product_id: Optional[str] = None


class NormalizedProduct(BaseModel):
    """
    Cleaned, normalized product ready for cross-platform matching.
    Output of the Normalizer.
    """

    platform: str
    raw_name: str
    normalized_name: str
    brand: Optional[str] = None
    product_type: Optional[str] = None
    variant: Optional[str] = None
    weight: Optional[WeightInfo] = None

    price: float
    mrp: Optional[float] = None
    discount_pct: Optional[float] = None
    unit_price: Optional[float] = None          # ₹ per 100g or 100ml
    unit_price_label: Optional[str] = None      # "₹20.00/100g"

    in_stock: bool = True
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[str] = None
    raw_weight_text: Optional[str] = None
    product_id: Optional[str] = None

    # Tokens used for matching (set by normalizer)
    name_tokens: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════
#  MATCH RESULTS
# ═══════════════════════════════════════════════


class MatchedPair(BaseModel):
    """Two products from different platforms identified as the same item."""

    canonical_name: str
    confidence: float                                  # 0.0–1.0
    confidence_label: ConfidenceLevel
    products: dict[str, NormalizedProduct]              # {"blinkit": ..., "instamart": ...}
    cheaper_platform: Optional[str] = None             # "blinkit" | "instamart" | None
    price_diff: float = 0.0                            # Absolute savings
    price_diff_pct: float = 0.0                        # Percentage savings
    unit_price_winner: Optional[str] = None
    unit_price_diff: Optional[float] = None
    match_details: dict[str, float] = Field(default_factory=dict)  # Per-strategy scores


class SearchMetadata(BaseModel):
    """Metadata about a search operation."""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    cache_hit: bool = False
    fetch_times: dict[str, float] = Field(default_factory=dict)
    total_time: float = 0.0
    platforms_available: list[str] = Field(default_factory=list)
    platforms_failed: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Complete matching output for a search query."""

    query: str
    location: Location
    matched_pairs: list[MatchedPair] = Field(default_factory=list)
    unmatched: dict[str, list[NormalizedProduct]] = Field(default_factory=dict)
    metadata: SearchMetadata = Field(default_factory=SearchMetadata)


# ═══════════════════════════════════════════════
#  CART & OPTIMIZER MODELS
# ═══════════════════════════════════════════════


class CartItemRequest(BaseModel):
    """A single item in the cart optimization request."""

    id: str
    canonical_name: str
    prices: dict[str, Optional[float]]      # {"blinkit": 14.0, "instamart": 13.0}
    in_stock: dict[str, bool] = Field(default_factory=dict)
    quantity: int = 1


class CartOptimizeRequest(BaseModel):
    """Request body for POST /api/cart/optimize."""

    items: list[CartItemRequest]


class PlatformCartBreakdown(BaseModel):
    """Cost breakdown for one platform."""

    platform: str
    platform_label: str
    items_total: float
    delivery_cost: float
    grand_total: float
    item_count: int
    has_oos_items: bool = False         # Does this platform have out-of-stock items?


class SplitAssignment(BaseModel):
    """Optimal split of cart items across platforms."""

    assignments: dict[str, str]         # {item_id: platform_id}
    platform_breakdowns: dict[str, PlatformCartBreakdown]
    grand_total: float
    num_deliveries: int


class CartOptimizationResult(BaseModel):
    """Full cart optimization response."""

    single_platform_totals: dict[str, PlatformCartBreakdown]
    optimal_split: Optional[SplitAssignment] = None
    recommendation: str                  # "all_blinkit" | "all_instamart" | "split"
    recommendation_reason: str
    savings_vs_worst: float = 0.0


# ═══════════════════════════════════════════════
#  DELIVERY INFO
# ═══════════════════════════════════════════════


class DeliveryInfo(BaseModel):
    """Delivery cost configuration for a platform."""

    platform: str
    base_fee: float
    free_above_threshold: float
    source: str = "default"             # "scraped" | "default"


# ═══════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════


class PlatformHealth(BaseModel):
    status: str                         # "up" | "down" | "degraded"
    last_check: Optional[str] = None
    avg_response_ms: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    platforms: dict[str, PlatformHealth] = Field(default_factory=dict)
    cache_size: int = 0
