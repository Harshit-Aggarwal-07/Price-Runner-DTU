# DTU Grocery Price Compare — Configuration

"""
Central configuration for all application constants.
Edit values here, not scattered across modules.
"""

from dataclasses import dataclass


# ── Location ──

@dataclass(frozen=True)
class LocationConfig:
    latitude: float = 28.7501
    longitude: float = 77.1177
    label: str = "DTU Campus"
    pincode: str = "110042"


DTU_LOCATION = LocationConfig()


# ── Cache ──

CACHE_TTL_SECONDS: int = 300          # 5 minutes
CACHE_MAX_SIZE: int = 100             # Max cached search results


# ── Scraping / Fetching ──

REQUEST_TIMEOUT_SECONDS: int = 10
MAX_RESULTS_PER_PLATFORM: int = 20
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# ── Matching ──

CONFIDENCE_HIGH_THRESHOLD: float = 0.80
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50
WEIGHT_TOLERANCE_PCT: float = 5.0     # ±5% weight difference allowed
DEFAULT_MATCHING_STRATEGY: str = "hybrid"


# ── Delivery ──

DELIVERY_CONFIG: dict = {
    "blinkit": {
        "base_fee": 25.0,
        "free_above": 99.0,
        "platform_label": "Blinkit",
    },
    "instamart": {
        "base_fee": 35.0,
        "free_above": 149.0,
        "platform_label": "Swiggy Instamart",
    },
}


# ── Cart Optimizer ──

SPLIT_CART_MIN_SAVINGS: float = 5.0   # Min ₹ savings to recommend split
MAX_CART_ITEMS_BRUTE_FORCE: int = 20  # Switch to greedy above this


# ── Server ──

HOST: str = "0.0.0.0"
PORT: int = 8000


# ── Enabled Platforms ──
# Add new platform IDs here to enable them. Each needs an adapter in app/adapters/.
ENABLED_PLATFORMS: list[str] = ["blinkit", "instamart"]
