"""
Product Normalizer — Cleans and structures raw product listings.

Extracts brand, weight/volume, variant from messy product names.
Computes unit prices (₹/100g) for fair cross-platform comparison.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.core.models import NormalizedProduct, RawListing, WeightInfo


# Load brand aliases from config
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

_brand_aliases: dict[str, str] = {}
_aliases_path = _CONFIG_DIR / "brand_aliases.json"
if _aliases_path.exists():
    with open(_aliases_path, encoding="utf-8") as f:
        _brand_aliases = json.load(f)

# Sorted by length descending so "coca-cola" matches before "coca"
_KNOWN_BRANDS = sorted(_brand_aliases.keys(), key=len, reverse=True)


# ── Weight Extraction Patterns ──

# Matches patterns like: 70g, 500 ml, 1.5 kg, 1L, 250 gm, 2 ltr
_WEIGHT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*"                         # number (possibly decimal)
    r"(kg|kgs|g|gm|gms|gram|grams|"               # weight units
    r"l|lt|ltr|litre|liter|litres|liters|ml|"      # volume units
    r"piece|pieces|pc|pcs|pack|unit|units)\b",     # count units
    re.IGNORECASE,
)

# Matches multipack patterns: "Pack of 4 x 70g", "4x70g", "4 × 70g"
_MULTIPACK_PATTERN = re.compile(
    r"(?:pack\s+of\s+)?(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*"
    r"(kg|g|gm|gms|ml|l|ltr|litre|liter)\b",
    re.IGNORECASE,
)

# Matches reverse multipack patterns: "70 g x 4", "69.5 g x 2"
_REVERSE_MULTIPACK_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|g|gm|gms|ml|l|ltr|litre|liter)\s*[x×]\s*(\d+)\b",
    re.IGNORECASE,
)

# Unit conversions to base units (grams or ml)
_UNIT_TO_BASE: dict[str, tuple[float, str]] = {
    "g": (1.0, "g"),
    "gm": (1.0, "g"),
    "gms": (1.0, "g"),
    "gram": (1.0, "g"),
    "grams": (1.0, "g"),
    "kg": (1000.0, "g"),
    "kgs": (1000.0, "g"),
    "ml": (1.0, "ml"),
    "l": (1000.0, "ml"),
    "lt": (1000.0, "ml"),
    "ltr": (1000.0, "ml"),
    "litre": (1000.0, "ml"),
    "liter": (1000.0, "ml"),
    "litres": (1000.0, "ml"),
    "liters": (1000.0, "ml"),
    "piece": (1.0, "units"),
    "pieces": (1.0, "units"),
    "pc": (1.0, "units"),
    "pcs": (1.0, "units"),
    "pack": (1.0, "units"),
    "unit": (1.0, "units"),
    "units": (1.0, "units"),
}

# Common promotional suffixes to strip
_PROMO_PATTERNS = [
    re.compile(r"\b(buy\s+\d+\s+get\s+\d+\s+free)\b", re.IGNORECASE),
    re.compile(r"\(\s*free\s+[^)]+\)", re.IGNORECASE),
    re.compile(r"\b(combo|offer|new|launch|limited\s+edition)\b", re.IGNORECASE),
    re.compile(r"[™®©]", re.IGNORECASE),
]

# Platform names to strip from product names
_PLATFORM_NAMES = re.compile(
    r"\b(blinkit|grofers|swiggy|instamart|zepto|bigbasket|jiomart)\b",
    re.IGNORECASE,
)


def normalize(raw: RawListing) -> NormalizedProduct:
    """
    Transform a raw platform listing into a normalized product.

    Pipeline:
    1. Clean name (lowercase, strip symbols, collapse whitespace)
    2. Extract brand
    3. Extract weight/volume
    4. Compute unit price
    5. Compute discount percentage
    6. Tokenize for matching
    """
    cleaned = _clean_name(raw.name)
    brand = _extract_brand(cleaned)
    full_weight_text = f"{raw.name} {raw.raw_weight_text or ''}".strip()
    weight = _extract_weight(full_weight_text)
    variant = _extract_variant(cleaned)

    # Compute unit price
    unit_price: Optional[float] = None
    unit_price_label: Optional[str] = None
    if weight and weight.base_value_grams > 0:
        # Price per 100 base units (100g or 100ml)
        unit_price = round((raw.price / weight.base_value_grams) * 100, 2)
        unit_price_label = f"₹{unit_price:.2f}/100{weight.base_unit}"

    # Compute discount percentage
    discount_pct: Optional[float] = None
    if raw.mrp and raw.mrp > 0 and raw.price < raw.mrp:
        discount_pct = round(((raw.mrp - raw.price) / raw.mrp) * 100, 1)

    # Tokenize: remove brand and weight tokens for purer matching
    name_tokens = _tokenize_for_matching(cleaned, brand, weight)

    return NormalizedProduct(
        platform=raw.platform,
        raw_name=raw.name,
        normalized_name=cleaned,
        brand=brand,
        product_type=None,  # Could be enhanced with category extraction
        variant=variant,
        weight=weight,
        price=raw.price,
        mrp=raw.mrp,
        discount_pct=discount_pct,
        unit_price=unit_price,
        unit_price_label=unit_price_label,
        in_stock=raw.in_stock,
        product_url=raw.product_url,
        image_url=raw.image_url,
        rating=raw.rating,
        rating_count=raw.rating_count,
        raw_weight_text=raw.raw_weight_text,
        product_id=raw.product_id,
        name_tokens=name_tokens,
    )


def _clean_name(name: str) -> str:
    """Lowercase, strip symbols, collapse whitespace."""
    text = name.lower().strip()

    # Remove promotional patterns
    for pattern in _PROMO_PATTERNS:
        text = pattern.sub("", text)

    # Remove platform names
    text = _PLATFORM_NAMES.sub("", text)

    # Normalize hyphens and special chars
    text = text.replace("–", "-").replace("—", "-")

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _extract_brand(cleaned_name: str) -> Optional[str]:
    """Extract and normalize brand name using alias dictionary."""
    for brand_key in _KNOWN_BRANDS:
        if brand_key in cleaned_name:
            return _brand_aliases[brand_key]
    return None


def _extract_weight(name: str) -> Optional[WeightInfo]:
    """
    Extract weight/volume from product name.

    Handles:
    - Simple: "70g", "500 ml", "1.5 kg"
    - Multipack: "Pack of 4 x 70g", "4x70g"
    """
    text = name.lower()

    # Try multipack first (more specific)
    multipack_match = _MULTIPACK_PATTERN.search(text)
    if multipack_match:
        count = int(multipack_match.group(1))
        per_unit = float(multipack_match.group(2))
        unit = multipack_match.group(3).lower()
        multiplier, base_unit = _UNIT_TO_BASE.get(unit, (1.0, "g"))
        total = count * per_unit * multiplier

        return WeightInfo(
            value=count * per_unit,
            unit=unit,
            base_value_grams=total,
            base_unit=base_unit,
            raw_text=multipack_match.group(0),
            is_multipack=True,
            pack_count=count,
        )

    # Try reverse multipack: "70 g x 4", "69.5 g x 2"
    rev_match = _REVERSE_MULTIPACK_PATTERN.search(text)
    if rev_match:
        per_unit = float(rev_match.group(1))
        unit = rev_match.group(2).lower()
        count = int(rev_match.group(3))
        multiplier, base_unit = _UNIT_TO_BASE.get(unit, (1.0, "g"))
        total = count * per_unit * multiplier

        return WeightInfo(
            value=count * per_unit,
            unit=unit,
            base_value_grams=total,
            base_unit=base_unit,
            raw_text=rev_match.group(0),
            is_multipack=True,
            pack_count=count,
        )

    # Try simple weight extraction
    weight_match = _WEIGHT_PATTERN.search(text)
    if weight_match:
        value = float(weight_match.group(1))
        unit = weight_match.group(2).lower()
        multiplier, base_unit = _UNIT_TO_BASE.get(unit, (1.0, "g"))

        return WeightInfo(
            value=value,
            unit=unit,
            base_value_grams=value * multiplier,
            base_unit=base_unit,
            raw_text=weight_match.group(0),
            is_multipack=False,
            pack_count=1,
        )

    return None


def _extract_variant(cleaned_name: str) -> Optional[str]:
    """Extract product variant (flavor/type) if recognizable."""
    common_variants = [
        "masala", "salted", "unsalted", "plain", "classic", "original",
        "toned", "full cream", "double toned", "skimmed", "slim",
        "diet", "zero sugar", "zero", "sugar free",
        "mint", "lemon", "orange", "mango", "strawberry", "chocolate",
        "vanilla", "butterscotch", "pista", "kesar", "elaichi",
        "spicy", "hot", "tangy", "sweet", "cream & onion",
        "magic masala", "tomato", "pudina", "peri peri",
        "multigrain", "whole wheat", "atta", "maida", "white",
        "brown", "milk", "dark", "white chocolate",
    ]
    for variant in common_variants:
        if variant in cleaned_name:
            return variant
    return None


def _tokenize_for_matching(
    cleaned_name: str,
    brand: Optional[str],
    weight: Optional[WeightInfo],
) -> list[str]:
    """
    Create token list for matching, stripping brand and weight tokens.

    This gives us the "core product description" for fuzzy comparison.
    """
    tokens = cleaned_name.split()

    # Remove brand tokens
    if brand:
        brand_tokens = set(brand.lower().split())
        tokens = [t for t in tokens if t not in brand_tokens]

    # Remove weight/number tokens
    if weight:
        weight_tokens = set(weight.raw_text.lower().split())
        tokens = [t for t in tokens if t not in weight_tokens]

    # Remove pure numbers and single characters
    tokens = [t for t in tokens if len(t) > 1 and not t.replace(".", "").isdigit()]

    # Remove common filler words
    filler = {"the", "of", "and", "&", "with", "for", "in", "-", "–", "—", "|"}
    tokens = [t for t in tokens if t not in filler]

    return tokens
